"""Prediction and inference command for Doushi CLI (predict)."""

import csv
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import typer
from rich.table import Table

from doushi.client import DoushiClient, DoushiAPIError
from doushi.ui import (
    console,
    err_console,
    print_error_panel,
    print_json,
    print_success,
)

predict_app = typer.Typer(help="Run live inference on trained Doushi AI models.")


def load_batch_file(file_path: Path) -> List[Dict[str, Any]]:
    """Load sample records from various file formats (.json, .parquet, .xls, .xlsx, .csv, .tsv)."""
    ext = file_path.suffix.lower()

    # 1. JSON
    if ext == ".json":
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict):
                return [data]
            raise ValueError("JSON file must contain an array of sample objects or a single sample object.")

    # 2. Parquet
    elif ext == ".parquet":
        try:
            import pandas as pd
            df = pd.read_parquet(file_path)
            return df.to_dict(orient="records")
        except ImportError:
            try:
                import pyarrow.parquet as pq
                table = pq.read_table(file_path)
                return table.to_pylist()
            except ImportError:
                raise ImportError(
                    "To read .parquet files, please install pandas or pyarrow: pip install pandas pyarrow"
                )

    # 3. Excel (.xls, .xlsx)
    elif ext in [".xls", ".xlsx"]:
        try:
            import pandas as pd
            df = pd.read_excel(file_path)
            return df.to_dict(orient="records")
        except ImportError:
            raise ImportError(
                "To read Excel files (.xls, .xlsx), please install pandas and openpyxl: pip install pandas openpyxl"
            )

    # 4. Delimited Text (CSV, TSV, TXT)
    else:
        delimiter = "\t" if ext == ".tsv" else ","
        samples: List[Dict[str, Any]] = []
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            sample_header = f.read(2048)
            f.seek(0)
            if ext != ".tsv" and ";" in sample_header and "," not in sample_header:
                delimiter = ";"
            
            reader = csv.DictReader(f, delimiter=delimiter)
            for row in reader:
                parsed_row = {}
                for k, v in row.items():
                    if v is None or v == "":
                        parsed_row[k] = None
                    else:
                        try:
                            parsed_row[k] = float(v) if "." in v else int(v)
                        except ValueError:
                            parsed_row[k] = v
                samples.append(parsed_row)
        return samples


@predict_app.command(name="predict")
def predict(
    project_id: str = typer.Argument(..., help="Unique ID of the trained project"),
    data: Optional[str] = typer.Option(
        None,
        "--data",
        "-d",
        help="JSON string of feature inputs (e.g. '{\"age\": 30, \"tenure\": 12}')",
    ),
    file_path: Optional[Path] = typer.Option(
        None,
        "--file",
        "-f",
        help="Path to CSV, JSON, Parquet, or Excel file containing batch samples for inference",
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output",
        "-o",
        help="Path to save prediction outputs (.csv or .json)",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output predictions as raw JSON",
    ),
) -> None:
    """Run live prediction using inline JSON, a CSV/JSON/Parquet/Excel file, or piped stdin."""
    client = DoushiClient()
    client.check_auth_or_exit()

    payload_data = None

    # 1. Check direct CLI JSON argument
    if data:
        try:
            payload_data = json.loads(data)
        except json.JSONDecodeError:
            print_error_panel(
                "Invalid JSON",
                f"Could not parse --data as valid JSON: {data}",
                remedy="Ensure proper quoting: --data '{\"feature_1\": 10, \"feature_2\": 20}'"
            )
            raise typer.Exit(code=1)

    # 2. Check file input
    elif file_path:
        try:
            payload_data = load_batch_file(file_path)
        except Exception as e:
            print_error_panel("File Loading Error", str(e))
            raise typer.Exit(code=1)

    # 3. Check stdin pipe
    elif not sys.stdin.isatty():
        stdin_content = sys.stdin.read().strip()
        if stdin_content:
            try:
                payload_data = json.loads(stdin_content)
            except json.JSONDecodeError:
                # Try parsing as CSV
                import io
                reader = csv.DictReader(io.StringIO(stdin_content))
                samples = [row for row in reader]
                if samples:
                    payload_data = samples
                else:
                    print_error_panel("Invalid Stdin Input", "Could not parse standard input as JSON or CSV.")
                    raise typer.Exit(code=1)

    if payload_data is None:
        print_error_panel(
            "Missing Input Data",
            "No prediction data provided.",
            remedy="Provide data using:\n  • --data '{\"feature\": 12}'\n  • --file test_data.csv\n  • cat test_data.csv | doushi predict <id>"
        )
        raise typer.Exit(code=1)

    # Execute Prediction
    is_interactive = sys.stdout.isatty() and not json_output
    if is_interactive:
        with console.status(f"[bold cyan]Computing prediction for project {project_id}...[/bold cyan]"):
            try:
                result = client.predict(project_id, payload_data)
            except DoushiAPIError as e:
                print_error_panel("Inference Failed", e.message, status_code=e.status_code)
                raise typer.Exit(code=1)
    else:
        try:
            result = client.predict(project_id, payload_data)
        except DoushiAPIError as e:
            err_console.print(f"Error: {e.message}")
            raise typer.Exit(code=1)

    # Output handling
    if output:
        if output.suffix.lower() == ".json":
            with open(output, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2)
        else:
            # Write CSV
            predictions = result.get("prediction") or result.get("predictions")
            if isinstance(predictions, list):
                with open(output, "w", encoding="utf-8", newline="") as f:
                    writer = csv.writer(f)
                    writer.writerow(["prediction"])
                    for p in predictions:
                        writer.writerow([p])
            else:
                with open(output, "w", encoding="utf-8") as f:
                    f.write(str(predictions))
        print_success(f"Predictions saved to {output}")
        return

    if json_output or not sys.stdout.isatty():
        print_json(result)
        return

    # Formatted Rich Output
    pred = result.get("prediction") if "prediction" in result else result.get("predictions")
    latency = result.get("latency_ms", "-")

    table = Table(title=f"Prediction Result (Latency: {latency}ms)", border_style="green")
    table.add_column("Sample #", style="dim", justify="right")
    table.add_column("Prediction", style="bold green")

    if isinstance(pred, list):
        for i, val in enumerate(pred[:50]):
            table.add_row(str(i + 1), str(val))
        if len(pred) > 50:
            table.add_row("...", f"[dim]and {len(pred) - 50} more samples[/dim]")
    else:
        table.add_row("1", str(pred))

    console.print(table)
