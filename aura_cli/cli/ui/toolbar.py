"""
Toolbar - Minimal action bar for Aura CLI.

Provides a clean, inline toolbar for contextual actions on tool results.
Replaces heavy bordered buttons with simple text-based actions.

Features:
    - Minimal inline design
    - Clear action indicators
    - Keyboard hint support
    - Contextual action visibility
"""

from typing import Callable, Optional

from rich.console import Console, RenderableType
from rich.text import Text

from aura_cli.cli.ui.constants import UIStyles
from aura_cli.cli.ui.display_facade import get_console


class ToolbarAction:
    """
    Represents a toolbar action.

    Attributes:
        key: Keyboard shortcut (e.g., "c", "e", "a")
        label: Action label (e.g., "Copy", "Expand")
        style: Rich style for the action
        callback: Function to execute
        enabled: Whether action is available
    """

    def __init__(
        self,
        key: str,
        label: str,
        style: str,
        callback: Optional[Callable] = None,
        enabled: bool = True,
    ):
        """Initialize the instance."""
        self.key = key
        self.label = label
        self.style = style
        self.callback = callback
        self.enabled = enabled


def create_toolbar_actions(
    can_copy: bool = True,
    can_expand: bool = True,
    can_run: bool = False,
    can_apply: bool = False,
    can_reject: bool = False,
    is_expanded: bool = False,
    has_output: bool = False,
    on_copy: Optional[Callable] = None,
    on_expand: Optional[Callable] = None,
    on_run: Optional[Callable] = None,
    on_apply: Optional[Callable] = None,
    on_reject: Optional[Callable] = None,
) -> RenderableType:
    """
    Create minimal inline toolbar with available actions.

    Args:
        can_copy: Show copy action
        can_expand: Show expand/collapse action
        can_run: Show run action
        can_apply: Show apply action
        can_reject: Show reject action
        is_expanded: Current expand state
        has_output: Has viewable output
        on_*: Callback functions

    Returns:
        Rich Text with inline actions
    """

    actions = []

    if can_copy:
        actions.append(ToolbarAction("c", "copiar", UIStyles.MUTED, on_copy))

    if can_expand:
        expand_label = "recolher" if is_expanded else "expandir"
        actions.append(ToolbarAction("e", expand_label, UIStyles.MUTED, on_expand))

    if can_apply:
        actions.append(ToolbarAction("y", "aplicar", UIStyles.SUCCESS, on_apply))

    if can_reject:
        actions.append(ToolbarAction("n", "rejeitar", UIStyles.ERROR, on_reject))

    if can_run:
        actions.append(ToolbarAction("r", "executar", UIStyles.SUCCESS, on_run))

    if has_output:
        actions.append(ToolbarAction("v", "ver", UIStyles.MUTED, None))

    # Build minimal inline text
    text = Text()
    text.append("  ", style="dim")

    for i, action in enumerate(actions):
        if i > 0:
            text.append("  │  ", style=f"dim {UIStyles.MUTED}")

        # Key hint
        text.append(f"[{action.key}]", style=f"dim {action.style}")
        text.append(" ", style="dim")
        # Label
        text.append(action.label, style=f"{action.style}")

    return text


def display_toolbar(
    tool_name: str,
    can_copy: bool = True,
    can_expand: bool = True,
    can_run: bool = False,
    can_apply: bool = False,
    can_reject: bool = False,
    is_expanded: bool = False,
    has_output: bool = False,
    on_copy: Optional[Callable] = None,
    on_expand: Optional[Callable] = None,
    on_run: Optional[Callable] = None,
    on_apply: Optional[Callable] = None,
    on_reject: Optional[Callable] = None,
    output_console: Optional[Console] = None,
) -> None:
    """
    Display minimal inline toolbar.

    Args:
        tool_name: Tool name for context
        can_*: Action availability flags
        on_*: Callback functions
    """
    toolbar = create_toolbar_actions(
        can_copy=can_copy,
        can_expand=can_expand,
        can_run=can_run,
        can_apply=can_apply,
        can_reject=can_reject,
        is_expanded=is_expanded,
        has_output=has_output,
        on_copy=on_copy,
        on_expand=on_expand,
        on_run=on_run,
        on_apply=on_apply,
        on_reject=on_reject,
    )

    target_console = output_console if output_console is not None else get_console()
    target_console.print(toolbar)


def create_idle_toolbar_hints() -> Text:
    """Return a minimal set of quick-access shortcut hints for the prompt footer."""
    text = Text()
    text.append("  ", style="dim")
    hints = [
        ("Ctrl+P", "palette"),
        ("/tui", "gui interface"),
        ("/agi", "agi mode"),
        ("/ops", "devops mode"),
        ("/help", "help"),
    ]
    for i, (key, label) in enumerate(hints):
        if i > 0:
            text.append("  │  ", style=f"dim {UIStyles.MUTED}")
        text.append(f"[{key}]", style=f"dim {UIStyles.INFO}")
        text.append(f" {label}", style=UIStyles.MUTED)
    return text


def create_action_hint(key: str, label: str, style: str = UIStyles.MUTED) -> Text:
    """
    Create a single action hint for inline display.

    Args:
        key: Keyboard shortcut
        label: Action label
        style: Text style

    Returns:
        Formatted action hint
    """
    hint = Text()
    hint.append(f"[{key}]", style=f"dim {style}")
    hint.append(f" {label}", style=style)
    return hint
