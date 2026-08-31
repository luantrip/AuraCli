"""Compatibility adapter for application tangent management."""

from typing import Any, Dict, List, Optional

from aura_cli.application.workspace.tangent import (
    ConversationCheckpoint,
    TangentState,
)
from aura_cli.application.workspace.tangent import (
    TangentManager as ApplicationTangentManager,
)


def _interactive_forget_selection(
    user_messages: List[Dict[str, Any]],
) -> Optional[int]:
    try:
        import questionary
        from rich.console import Console

        choices = [
            questionary.Choice(title=f"[{index}] {info['preview']}", value=index)
            for index, info in enumerate(reversed(user_messages), 1)
        ]
        choices.append(questionary.Choice(title="[Cancel]", value=0))
        console = Console()
        console.print("\n[bold cyan]Select how many recent messages to forget:[/]")
        console.print("[dim]Messages shown from most recent to oldest[/]\n")
        result = questionary.select(
            "Forget up to (and including):", choices=choices, use_shortcuts=True
        ).ask()
        return result if result else 0
    except ImportError:
        try:
            return int(
                input(f"How many messages to forget? (1-{len(user_messages)}): ")
            )
        except (ValueError, KeyboardInterrupt):
            return None
    except Exception:
        return 1


class TangentManager(ApplicationTangentManager):
    """Application manager configured with the terminal selection adapter."""

    def __init__(self) -> None:
        super().__init__(forget_selector=_interactive_forget_selection)


__all__ = ["ConversationCheckpoint", "TangentManager", "TangentState"]
