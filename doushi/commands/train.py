"""Model training and creation command for Doushi CLI (train / create)."""

import os
import sys
import time
from pathlib import Path
from typing import Optional
import typer
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from doushi.client import DoushiClient, DoushiAPIError
from doushi.ui import (
    console,
    err_console,
    print_banner,
    print_error_panel,
    print_info,
    print_json,
    print_success,
    print_warning,
)

train_app = typer.Typer(help="Train and build autonomous ML models from datasets.")


@train_app.command(name="train")
@train_app.command(name="create")
def train(
    dataset_file: Path = typer.Argument(
        ...,
        help="Path to local dataset file (.csv, .parquet, .xlsx, .tsv, .json)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
    ),
    goal: Optional[str] = typer.Option(
        None,
        "--goal",
        "-g",
        help="Natural language prediction goal (e.g. 'Predict customer churn probability')",
    ),
    name: Optional[str] = typer.Option(
        None,
        "--name",
        "-n",
        help="Project name (defaults to dataset filename)",
    ),
    follow: bool = typer.Option(
        True,
        "--follow/--no-follow",
        "-f/-F",
        help="Stream agent progress until model training completes.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output created project details as JSON",
    ),
) -> None:
    """Upload dataset and train an autonomous ML model with agent self-healing."""
    client = DoushiClient()
    client.check_auth_or_exit()

    # 1. Fetch user account info for tier limit verification
    with console.status("[bold cyan]Checking account quotas & tier limits...[/bold cyan]"):
        try:
            whoami_data = client.get_whoami()
            org = whoami_data.get("organization") or {}
            tier = str(org.get("tier", "free")).lower()
        except Exception:
            tier = "free"

    # 2. Local Pre-flight check on dataset size
    client.check_file_limits(dataset_file, tier=tier)

    # 3. Prompt for goal if missing
    if not goal:
        print_banner()
        console.print(f"\n[bold white]Dataset:[/bold white] [bold cyan]{dataset_file.name}[/bold cyan]")
        console.print(f"[bold white]Size:[/bold white]    [dim]{dataset_file.stat().st_size / (1024*1024):.2f} MB[/dim]\n")
        goal = Prompt.ask(
            "[bold green]🎯 What is your prediction goal for this dataset?[/bold green]\n"
            "[dim](e.g. 'Predict customer churn', 'Forecast monthly revenue', 'Classify spam')[/dim]"
        )
        if not goal or not goal.strip():
            print_error_panel("Goal Required", "A prediction goal is required for the autonomous agent to build the model.")
            raise typer.Exit(code=1)

    project_name = name or dataset_file.stem.replace("_", " ").replace("-", " ").title()

    # 4. Create Project
    with console.status(f"[bold cyan]Initializing project '{project_name}'...[/bold cyan]"):
        try:
            proj_data = client.create_project(name=project_name)
            project_id = proj_data.get("project_id") or proj_data.get("id")
        except DoushiAPIError as e:
            print_error_panel("Project Creation Failed", e.message, status_code=e.status_code)
            raise typer.Exit(code=1)

    # 5. Request S3 presigned URL
    file_size = dataset_file.stat().st_size
    with console.status("[bold cyan]Requesting secure storage upload URL...[/bold cyan]"):
        try:
            upload_info = client.request_upload_url(
                project_id=project_id,
                filename=dataset_file.name,
                file_size=file_size,
            )
            presigned_url = upload_info["url"]
        except DoushiAPIError as e:
            print_error_panel("Upload Request Failed", e.message, status_code=e.status_code)
            raise typer.Exit(code=1)

    # 6. Stream upload file to S3
    client.upload_file_to_s3(presigned_url, dataset_file)
    print_success(f"Dataset '{dataset_file.name}' uploaded successfully.")

    # 7. Start Agent Pipeline
    with console.status("[bold cyan]Dispatching autonomous agent pipeline...[/bold cyan]"):
        try:
            client.start_pipeline(project_id=project_id, prompt=goal)
        except DoushiAPIError as e:
            print_error_panel("Agent Dispatch Failed", e.message, status_code=e.status_code)
            raise typer.Exit(code=1)

    print_success(f"Autonomous agent started for project [bold cyan]{project_id}[/bold cyan].")

    if json_output:
        print_json({
            "project_id": project_id,
            "name": project_name,
            "goal": goal,
            "dataset": dataset_file.name,
            "status": "queued"
        })
        return

    if not follow:
        console.print(f"\n👉 Track status: [bold cyan]doushi view {project_id}[/bold cyan]")
        console.print(f"👉 Stream logs:  [bold cyan]doushi logs {project_id} -f[/bold cyan]\n")
        return

    # 8. Follow / Stream agent progress
    console.print("\n[bold white]Watching Autonomous Agent Execution[/bold white] [dim](Press Ctrl+C to detach)[/dim]\n")

    last_status = None
    with console.status("[bold yellow]Agent analyzing dataset schema & selecting ML strategy...[/bold yellow]") as status_spinner:
        for _ in range(120):  # Wait up to 10 minutes
            time.sleep(5)
            try:
                p = client.get_project(project_id)
            except Exception:
                continue

            current_status = str(p.get("status", "pending")).lower()

            if current_status != last_status:
                last_status = current_status
                if current_status in ["queued", "pending"]:
                    status_spinner.update("[bold blue]Job queued in compute worker...[/bold blue]")
                elif current_status in ["running", "training"]:
                    status_spinner.update("[bold yellow]Agent executing sandbox code & optimizing hyperparameters...[/bold yellow]")
                elif current_status == "success":
                    break
                elif current_status == "failed":
                    break

        if current_status == "success":
            console.print("\n")
            print_success(f"Model successfully trained and ready for inference!")
            
            metrics = p.get("metrics") or {}
            if isinstance(metrics, dict) and metrics:
                m_table = Table(title="Model Evaluation Performance", border_style="green")
                m_table.add_column("Metric", style="bold white")
                m_table.add_column("Score", style="bold green")
                for k, v in metrics.items():
                    val_str = f"{v:.4f}" if isinstance(v, (int, float)) else str(v)
                    m_table.add_row(k.upper(), val_str)
                console.print(m_table)

            console.print("\n[bold green]✦ Next Steps:[/bold green]")
            console.print(f"  • Run live prediction:   [bold cyan]doushi predict {project_id} --data '{{...}}'[/bold cyan]")
            console.print(f"  • Export model & code:   [bold cyan]doushi export {project_id} --out ./model-bundle/[/bold cyan]")
            console.print(f"  • Inspect project:       [bold cyan]doushi view {project_id}[/bold cyan]\n")

        elif current_status == "failed":
            console.print("\n")
            err_msg = p.get("error") or "Unknown error occurred during agent training."
            print_error_panel(
                title="Model Training Failed",
                message=str(err_msg),
                remedy=f"View full agent traceback with: doushi logs {project_id}"
            )
            raise typer.Exit(code=1)
