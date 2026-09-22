"""Doushi CLI Main Entry Point."""

import sys
from pathlib import Path

# Ensure parent directory is in sys.path when running file directly (python doushi/main.py)
parent_dir = str(Path(__file__).resolve().parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from typing import Optional
import typer
from rich.console import Console

from doushi import __app_name__, __version__
from doushi.commands.auth import auth_app, configure, whoami, logout
from doushi.commands.projects import projects_app, list_projects, view_project, delete_project
from doushi.commands.train import train_app, train
from doushi.commands.predict import predict_app, predict
from doushi.commands.logs import logs_app, logs
from doushi.commands.export import export_app, export_model
from doushi.commands.demo import demo_app, run_demo
from doushi.ui import print_banner

app = typer.Typer(
    name=__app_name__,
    help="✦ Doushi.ai CLI - Instant Autonomous ML Modeling & Inference from your Terminal ✦",
    add_completion=True,
    rich_markup_mode="rich",
    no_args_is_help=True,
)

# Top-level direct shortcuts for the most common commands
app.command(name="configure", help="Set up and verify your Doushi API Key.")(configure)
app.command(name="login", help="Authenticate with Doushi.ai.")(configure)
app.command(name="whoami", help="View authenticated user account and tier quotas.")(whoami)
app.command(name="logout", help="Log out and remove local credentials.")(logout)

app.command(name="train", help="Upload dataset & train an autonomous ML model.")(train)
app.command(name="create", help="Alias for train.")(train)

app.command(name="predict", help="Run inference on a trained model (JSON, CSV, XLS or PARQUET).")(predict)
app.command(name="logs", help="Stream agent execution & self-healing sandbox logs.")(logs)
app.command(name="export", help="Export model.pkl + standalone FastAPI microservice & Dockerfile.")(export_model)
app.command(name="demo", help="Run an instant 30-second autonomous modeling demo.")(run_demo)

# Subcommand Groups
app.add_typer(projects_app, name="projects", help="Manage and inspect projects.")


def version_callback(value: bool) -> None:
    if value:
        print_banner()
        typer.echo(f"Version: {__version__}")
        raise typer.Exit()


@app.callback(context_settings={"help_option_names": ["-h", "--help"]})
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        "-v",
        help="Show version and exit.",
        callback=version_callback,
        is_eager=True,
    ),
) -> None:
    """✦ Doushi CLI - Autonomous Machine Learning in your Terminal ✦"""
    pass


def cli() -> None:
    """Entrypoint function ensuring consistent 'doushi' command name in help."""
    app(prog_name="doushi")


if __name__ == "__main__":
    cli()
