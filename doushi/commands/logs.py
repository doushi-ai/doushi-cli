"""Log streaming and inspection commands for Doushi CLI (logs)."""

import time
from typing import Optional
import typer
from rich.panel import Panel

from doushi.client import DoushiClient, DoushiAPIError
from doushi.ui import (
    console,
    err_console,
    print_error_panel,
    print_info,
    print_json,
)

logs_app = typer.Typer(help="Stream and inspect agent execution and self-healing logs.")


@logs_app.command(name="logs")
def logs(
    project_id: str = typer.Argument(..., help="Unique ID of the project"),
    follow: bool = typer.Option(
        False,
        "--follow",
        "-f",
        help="Continuously stream new logs until execution finishes",
    ),
    raw: bool = typer.Option(
        False,
        "--raw",
        help="Print raw unformatted logs",
    ),
) -> None:
    """View training agent logs, sandbox execution, and self-healing tracebacks."""
    client = DoushiClient()
    client.check_auth_or_exit()

    last_logs = ""

    while True:
        try:
            p = client.get_project(project_id)
        except DoushiAPIError as e:
            print_error_panel("Failed to Fetch Logs", e.message, status_code=e.status_code)
            raise typer.Exit(code=1)

        project_logs = p.get("logs") or ""
        error = p.get("error")
        status = str(p.get("status", "pending")).lower()

        if project_logs and project_logs != last_logs:
            # Print only new log lines if following
            if last_logs and project_logs.startswith(last_logs):
                new_part = project_logs[len(last_logs):]
            else:
                new_part = project_logs

            if raw:
                print(new_part, end="")
            else:
                for line in new_part.splitlines():
                    if "ERROR" in line or "Traceback" in line or "Exception" in line:
                        console.print(f"[bold red]{line}[/bold red]")
                    elif "WARNING" in line:
                        console.print(f"[bold yellow]{line}[/bold yellow]")
                    elif "INFO" in line or "Success" in line:
                        console.print(f"[bold green]{line}[/bold green]")
                    else:
                        console.print(f"[dim]{line}[/dim]")

            last_logs = project_logs

        if not follow:
            if not project_logs:
                console.print(f"[dim]No logs available yet for project {project_id}. Status: {status}[/dim]")
            if error:
                print_error_panel("Project Error", str(error))
            break

        if status in ["success", "failed"]:
            console.print(f"\n[bold]Execution finished with status: [/bold]{status.upper()}")
            break

        time.sleep(3)
