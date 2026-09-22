"""Authentication commands for Doushi CLI (configure, login, whoami, logout)."""

import sys
import webbrowser
from typing import Optional
import typer
from rich.prompt import Prompt
from rich.panel import Panel
from rich.table import Table

from doushi.config import (
    DEFAULT_DASHBOARD_URL,
    delete_credentials,
    get_api_key,
    load_credentials,
    save_credentials,
)
from doushi.client import DoushiClient, DoushiAPIError
from doushi.ui import (
    console,
    err_console,
    print_banner,
    print_error_panel,
    print_info,
    print_json,
    print_success,
)

auth_app = typer.Typer(help="Manage authentication and API credentials.")


@auth_app.command(name="configure")
@auth_app.command(name="login")
def configure(
    key: Optional[str] = typer.Option(
        None,
        "--key",
        "-k",
        help="Doushi API Key (dsh_live_...)",
    ),
    no_browser: bool = typer.Option(
        False,
        "--no-browser",
        help="Do not automatically open the browser to the API keys page.",
    ),
) -> None:
    """Configure your Doushi API Key to authenticate the CLI."""
    print_banner()
    console.print("\n[bold white]Authenticate with Doushi.ai[/bold white]\n")

    api_keys_url = f"{DEFAULT_DASHBOARD_URL}/settings/api-keys"

    if not key:
        if not no_browser:
            console.print(f"👉 Opening your browser to generate or copy an API Key:\n   [bold cyan underline]{api_keys_url}[/bold cyan underline]\n")
            try:
                webbrowser.open(api_keys_url)
            except Exception:
                pass
        else:
            console.print(f"👉 Visit your dashboard to generate or copy an API Key:\n   [bold cyan underline]{api_keys_url}[/bold cyan underline]\n")

        key = Prompt.ask(
            "[bold green]🔑 Paste your Doushi API Key[/bold green] (starts with 'dsh_live_')",
            password=True,
        )

    key = key.strip()
    if not key:
        print_error_panel(
            title="Invalid Key",
            message="No API Key provided. Authentication aborted."
        )
        raise typer.Exit(code=1)

    # Validate against backend API
    with console.status("[bold cyan]Verifying API Key with Doushi.ai...[/bold cyan]"):
        client = DoushiClient(api_key=key)
        try:
            user_data = client.get_whoami()
        except DoushiAPIError as e:
            print_error_panel(
                title="Authentication Failed",
                message=f"The provided API Key could not be verified: {e.message}",
                remedy="Double check the key in your dashboard at https://doushi.ai/settings/api-keys"
            )
            raise typer.Exit(code=1)
        except Exception as e:
            print_error_panel(
                title="Connection Error",
                message=f"Could not reach Doushi backend: {str(e)}",
                remedy="Check your internet connection or backend status."
            )
            raise typer.Exit(code=1)

    user_email = user_data.get("email") or user_data.get("id", "Unknown User")
    org = user_data.get("organization") or {}
    org_name = org.get("name", "Personal Workspace")
    tier = str(org.get("tier", "free")).capitalize()

    save_credentials(
        api_key=key,
        user_email=user_email,
        org_name=org_name,
        tier=tier
    )

    console.print("\n")
    print_success("Successfully authenticated with Doushi.ai!")
    
    table = Table(show_header=False, border_style="green", box=None)
    table.add_row("[bold white]User Account:[/bold white]", f"[cyan]{user_email}[/cyan]")
    table.add_row("[bold white]Organization:[/bold white]", f"[white]{org_name}[/white]")
    table.add_row("[bold white]Active Plan:[/bold white]", f"[bold yellow]{tier}[/bold yellow]")
    table.add_row("[bold white]Credentials Saved:[/bold white]", "[dim]~/.doushi/credentials (mode 0600)[/dim]")
    
    console.print(Panel(table, title="[bold green]✦ Authentication Active ✦[/bold green]", border_style="green"))
    console.print("\n[dim]Ready! Run `doushi train <dataset.csv>` or `doushi demo` to start building models.[/dim]\n")


@auth_app.command(name="whoami")
def whoami(
    json_output: bool = typer.Option(False, "--json", help="Output information as JSON"),
) -> None:
    """View active authenticated user, organization, and tier quota."""
    client = DoushiClient()
    client.check_auth_or_exit()

    with console.status("[bold cyan]Fetching account details...[/bold cyan]"):
        try:
            data = client.get_whoami()
        except DoushiAPIError as e:
            print_error_panel("Account Verification Error", e.message, status_code=e.status_code)
            raise typer.Exit(code=1)

    if json_output:
        print_json(data)
        return

    user_email = data.get("email") or data.get("id", "Unknown")
    org = data.get("organization") or {}
    org_name = org.get("name", "Personal")
    tier = str(org.get("tier", "free")).capitalize()
    
    projects_count = data.get("projects_count", "-")
    max_projects = data.get("max_projects", 3 if tier.lower() == "free" else 15 if tier.lower() == "starter" else 100)

    table = Table(title="Doushi.ai Account Information", border_style="cyan")
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("User Email", user_email)
    table.add_row("User ID", str(data.get("id", "-")))
    table.add_row("Organization", org_name)
    table.add_row("Plan Tier", f"[bold yellow]{tier}[/bold yellow]")
    table.add_row("Projects", f"{projects_count} / {max_projects}")
    table.add_row("API Key Preview", f"...{client.api_key[-8:]}" if client.api_key else "None")

    console.print(table)


@auth_app.command(name="logout")
def logout() -> None:
    """Log out and remove local credentials."""
    delete_credentials()
    print_success("Logged out. Local credentials removed from ~/.doushi/credentials.")
