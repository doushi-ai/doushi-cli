"""Rich terminal UI and formatting utilities for Doushi CLI."""

import json
import sys
from typing import Any, Dict, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()
err_console = Console(stderr=True)


def print_banner() -> None:
    """Print the Doushi ASCII art banner."""
    banner_text = Text()
    banner_text.append("✦ ", style="bold cyan")
    banner_text.append("DOUSHI.AI", style="bold white")
    banner_text.append(" - Autonomous ML Platform CLI", style="dim white")
    console.print(banner_text)


def print_success(message: str) -> None:
    """Print success message with green checkmark."""
    console.print(f"[bold green]✔[/bold green] {message}")


def print_info(message: str) -> None:
    """Print informational message with cyan bullet."""
    console.print(f"[bold cyan]ℹ[/bold cyan] {message}")


def print_warning(message: str) -> None:
    """Print warning message with yellow alert icon."""
    console.print(f"[bold yellow]⚠️[/bold yellow]  {message}")


def print_error_panel(
    title: str,
    message: str,
    remedy: Optional[str] = None,
    upgrade_url: Optional[str] = None,
    status_code: Optional[int] = None
) -> None:
    """Render a clean, high-visibility error panel."""
    content = Text()
    content.append(message, style="white")
    
    if remedy:
        content.append("\n\n💡 Recommended Action:\n", style="bold yellow")
        content.append(remedy, style="bright_white")
        
    if upgrade_url:
        content.append(f"\n👉 Upgrade plan: {upgrade_url}\n", style="bold cyan underline")
        
    panel_title = f"[bold red]❌ {title}[/bold red]"
    if status_code:
        panel_title += f" [dim](HTTP {status_code})[/dim]"
        
    err_console.print(
        Panel(
            content,
            title=panel_title,
            border_style="red",
            padding=(1, 2)
        )
    )


def print_tier_limit_error(file_name: str, file_size_mb: float, tier: str, max_mb: float) -> None:
    """Render a detailed dataset size limit error."""
    msg = (
        f"Your dataset '[bold]{file_name}[/bold]' is [bold red]{file_size_mb:.1f} MB[/bold red], "
        f"which exceeds the [bold]{max_mb:.0f} MB[/bold] limit for your current plan ([cyan]{tier.capitalize()}[/cyan]).\n\n"
        f"  📊 Dataset Size:  [bold]{file_size_mb:.1f} MB[/bold]\n"
        f"  🔒 Plan Limit:    [bold]{max_mb:.0f} MB[/bold]"
    )
    remedy = (
        "1. Subsample your CSV locally:\n"
        f"   head -n 25000 {file_name} > sample_{file_name}\n"
        "2. Or upgrade your organization tier to unlock higher file limits."
    )
    print_error_panel(
        title="Dataset Size Limit Exceeded",
        message=msg,
        remedy=remedy,
        upgrade_url="https://doushi.ai/billing"
    )


def print_projects_table(projects: List[Dict[str, Any]]) -> None:
    """Render a beautiful table of user projects."""
    if not projects:
        console.print("[dim]No projects found. Run `doushi train <dataset.csv>` to create one.[/dim]")
        return

    table = Table(title="Your Doushi AI Projects", border_style="dim")
    table.add_column("Project ID", style="cyan", no_wrap=True)
    table.add_column("Name", style="bold white")
    table.add_column("Status", style="bold")
    table.add_column("Best Metric", style="green")
    table.add_column("Model Type", style="dim")
    table.add_column("Created", style="dim")

    status_styles = {
        "success": "[bold green]● Ready[/bold green]",
        "training": "[bold yellow]◐ Training[/bold yellow]",
        "running": "[bold yellow]◐ Running[/bold yellow]",
        "queued": "[bold blue]○ Queued[/bold blue]",
        "failed": "[bold red]✖ Failed[/bold red]",
        "pending": "[dim]○ Pending[/dim]",
    }

    for p in projects:
        status_raw = str(p.get("status", "pending")).lower()
        status_display = status_styles.get(status_raw, f"[dim]{status_raw}[/dim]")
        
        metrics = p.get("metrics") or {}
        best_metric = "-"
        if isinstance(metrics, dict):
            for k in ["f1", "f1_score", "accuracy", "roc_auc", "r2", "rmse"]:
                if k in metrics:
                    val = metrics[k]
                    best_metric = f"{k.upper()}: {val:.4f}" if isinstance(val, (int, float)) else f"{k}: {val}"
                    break
                    
        model_type = p.get("model_type") or p.get("provider") or "-"
        created_at = str(p.get("created_at", "-"))[:10]

        table.add_row(
            p.get("id", "-"),
            p.get("name", "Untitled Project"),
            status_display,
            best_metric,
            str(model_type),
            created_at
        )

    console.print(table)


def print_json(data: Any) -> None:
    """Print clean formatted JSON to stdout for pipes/scripts."""
    print(json.dumps(data, indent=2, default=str))
