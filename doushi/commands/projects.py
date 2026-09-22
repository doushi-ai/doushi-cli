"""Project management commands for Doushi CLI (list, view, delete, init)."""

from typing import Optional
import typer
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from doushi.client import DoushiClient, DoushiAPIError
from doushi.ui import (
    console,
    err_console,
    print_error_panel,
    print_info,
    print_json,
    print_projects_table,
    print_success,
    print_warning,
)

projects_app = typer.Typer(help="Manage and inspect your Doushi AI projects.")


@projects_app.command(name="list")
@projects_app.command(name="ls")
def list_projects(
    json_output: bool = typer.Option(False, "--json", help="Output list as JSON"),
) -> None:
    """List all AI projects in your organization."""
    client = DoushiClient()
    with console.status("[bold cyan]Fetching projects...[/bold cyan]"):
        try:
            projects = client.list_projects()
        except DoushiAPIError as e:
            print_error_panel("Failed to List Projects", e.message, status_code=e.status_code)
            raise typer.Exit(code=1)

    if json_output:
        print_json(projects)
        return

    print_projects_table(projects)


@projects_app.command(name="view")
def view_project(
    project_id: str = typer.Argument(..., help="Unique ID of the project"),
    json_output: bool = typer.Option(False, "--json", help="Output details as JSON"),
) -> None:
    """View detailed metrics, hyperparameters, and status for a project."""
    client = DoushiClient()
    with console.status(f"[bold cyan]Fetching project {project_id}...[/bold cyan]"):
        try:
            p = client.get_project(project_id)
        except DoushiAPIError as e:
            print_error_panel("Project Not Found", e.message, status_code=e.status_code)
            raise typer.Exit(code=1)

    if json_output:
        print_json(p)
        return

    status = str(p.get("status", "unknown")).upper()
    name = p.get("name", "Untitled")

    console.print(f"\n[bold white]Project:[/bold white] [bold cyan]{name}[/bold cyan] ([dim]{project_id}[/dim])")
    console.print(f"[bold white]Status:[/bold white] [bold]{status}[/bold]\n")

    # Overview table
    table = Table(title="Project Details", border_style="dim")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("ID", str(p.get("id", "-")))
    table.add_row("Name", name)
    table.add_row("Status", status)
    table.add_row("Prompt Goal", str(p.get("prompt", "-")))
    table.add_row("Dataset Path", str(p.get("dataset_path", "-")))
    table.add_row("Model Provider", str(p.get("provider", "gemini")))
    table.add_row("Current Iteration", str(p.get("current_iteration", 0)))
    table.add_row("Created At", str(p.get("created_at", "-")))

    console.print(table)

    # Metrics section
    metrics = p.get("metrics")
    if metrics and isinstance(metrics, dict):
        m_table = Table(title="Model Evaluation Metrics", border_style="green")
        m_table.add_column("Metric", style="bold white")
        m_table.add_column("Score", style="bold green")
        for k, v in metrics.items():
            if isinstance(v, (int, float)):
                m_table.add_row(k.upper(), f"{v:.4f}")
            else:
                m_table.add_row(k.upper(), str(v))
        console.print(m_table)

    # Error section
    error = p.get("error")
    if error:
        print_error_panel("Model Failure Error", str(error))


@projects_app.command(name="delete")
def delete_project(
    project_id: str = typer.Argument(..., help="Unique ID of the project to delete"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt"),
) -> None:
    """Delete a project and its associated artifacts."""
    client = DoushiClient()

    if not yes:
        confirm = Confirm.ask(f"[bold yellow]Are you sure you want to permanently delete project '{project_id}'?[/bold yellow]")
        if not confirm:
            print_info("Deletion cancelled.")
            return

    with console.status(f"[bold red]Deleting project {project_id}...[/bold red]"):
        try:
            client.delete_project(project_id)
        except DoushiAPIError as e:
            print_error_panel("Deletion Failed", e.message, status_code=e.status_code)
            raise typer.Exit(code=1)

    print_success(f"Project '{project_id}' successfully deleted.")
