"""Cost command handler for Aura CLI.

Handles commands:
- /cost: Display token usage and estimated cost for the current session.
"""

from typing import Optional

from rich.panel import Panel
from rich.table import Table

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import display_info, get_console
from aura_cli.core.stats import get_stats


def handle_cost(args: str = "") -> Optional[str]:
    """Display token usage and estimated cost for the current session.

    Shows:
        - Total tokens used
        - Estimated cost in USD
        - Breakdown by model (if multiple models used)
        - Session duration

    Args:
        args: Optional arguments (unused for now).

    Returns:
        None (outputs directly to console).
    """
    stats = get_stats()
    summary = stats.get_cost_summary()

    if summary["total_tokens"] == 0:
        # Simple status message → route through the display funnel.
        display_info("No tokens used this session yet.")
        return None

    # Main summary table
    table = Table(
        show_header=False,
        border_style=UIStyles.BORDER_PRIMARY,
        padding=(0, 1),
    )
    table.add_column("Metric", style="bold")
    table.add_column("Value", style="cyan")

    table.add_row("Total Tokens", f"{summary['total_tokens']:,}")
    table.add_row("  Prompt", f"{summary['prompt_tokens']:,}")
    table.add_row("  Completion", f"{summary['completion_tokens']:,}")
    table.add_row("Estimated Cost", f"${summary['estimated_cost_usd']:.4f} USD")
    table.add_row("Session Duration", summary["session_duration"])

    # Model breakdown
    breakdown = summary.get("breakdown_by_model", {})
    if breakdown:
        table.add_row("", "")  # spacer
        table.add_row("[bold]Model Breakdown[/]", "")
        for model_name, model_data in breakdown.items():
            short_name = model_name.split("/")[-1] if "/" in model_name else model_name
            tokens_str = f"{model_data['total_tokens']:,} tokens"
            cost_str = f"${model_data['estimated_cost_usd']:.4f}"
            rate_str = f"(${model_data['rate_per_1m']:.2f}/1M)"
            table.add_row(f"  {short_name}", f"{tokens_str} — {cost_str} {rate_str}")

    panel = Panel(
        table,
        title=f"[{UIStyles.TITLE}]{UIIcons.INFO} Session Cost Summary[/]",
        border_style=UIStyles.BORDER_PRIMARY,
    )

    # Composed renderable → use the shared funnel console (not a fresh console).
    console = get_console()
    console.print()
    console.print(panel)
    console.print()
    return None
