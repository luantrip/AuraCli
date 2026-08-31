"""Apply/Reject system for Aura CLI - Change application and rejection.

This module provides the ApplyState enum and the display_apply_reject_actions
helper used by the toolbar. The canonical diff confirmation flow lives in
``cli/tool_execution._show_diff_confirmation()``.

Change States:
    - NOT_STARTED: Change registered but not processed
    - STREAMING: Change being applied (in progress)
    - DONE: Change applied successfully
    - CLOSED: Change rejected or cancelled
    - ERROR: Error applying change
"""

from datetime import datetime
import difflib
from enum import Enum
import os
import time
from typing import Any, Callable, Dict, List, Optional

from rich.columns import Columns
from rich.console import Group
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.clipboard import copy_code
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console

console = get_console()


class ApplyState(Enum):
    """Possible states for change application.

    Values:
        NOT_STARTED: Change registered but not processed
        STREAMING: Change being applied
        DONE: Change applied successfully
        CLOSED: Change rejected or cancelled
        ERROR: Error applying change
    """

    NOT_STARTED = "not-started"
    STREAMING = "streaming"
    DONE = "done"
    CLOSED = "closed"
    ERROR = "error"


class ApplyRejectManager:
    """Manages application and rejection of file changes.

    Tracks changes across three dicts: pending_changes, applied_changes
    and rejected_changes. The canonical diff confirmation flow uses
    ``_show_diff_confirmation()`` in ``cli/tool_execution.py``. Use this
    class only for external integrations (extensions, plugins).
    """

    def __init__(self):
        """Initialize the instance."""
        self.pending_changes: dict = {}
        self.applied_changes: dict = {}
        self.rejected_changes: dict = {}
        self.change_history: List[Dict[str, Any]] = []

    def register_change(
        self,
        change_id: str,
        file_path: str,
        old_content: str,
        new_content: str,
        description: Optional[str] = None,
    ) -> None:
        """Register a pending change.

        Args:
            change_id: Unique change identifier.
            file_path: Target file path.
            old_content: Current file content.
            new_content: Proposed file content.
            description: Optional human-readable description.
        """
        self.pending_changes[change_id] = {
            "file_path": file_path,
            "old_content": old_content,
            "new_content": new_content,
            "description": description,
            "state": ApplyState.NOT_STARTED,
        }

    def apply_change(self, change_id: str) -> bool:
        """Apply a pending change, writing the new content to disk.

        Creates a .aura_backup before overwriting. Moves the change to
        applied_changes on success.

        Args:
            change_id: Change identifier.

        Returns:
            True if the file was written successfully.
        """
        if change_id not in self.pending_changes:
            return False

        change = self.pending_changes[change_id]
        file_path = change["file_path"]
        new_content = change["new_content"]

        try:
            if os.path.exists(file_path):
                backup_path = f"{file_path}.aura_backup"
                with open(file_path, encoding="utf-8") as f:
                    old_content = f.read()
                with open(backup_path, "w", encoding="utf-8") as f:
                    f.write(old_content)

            os.makedirs(
                os.path.dirname(file_path) if os.path.dirname(file_path) else ".",
                exist_ok=True,
            )
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            change["state"] = ApplyState.DONE
            change["applied_at"] = time.time()
            self.applied_changes[change_id] = change
            del self.pending_changes[change_id]

            # Add to history
            self.change_history.append(
                {
                    "change_id": change_id,
                    "file_path": file_path,
                    "action": "applied",
                    "timestamp": time.time(),
                    "description": change.get("description"),
                }
            )

            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} Changes applied to {file_path}[/{UIStyles.SUCCESS}]"
            )
            return True
        except Exception as e:
            change["state"] = ApplyState.ERROR
            console.print(
                f"[{UIStyles.ERROR}]{UIIcons.ERROR} Failed to apply changes: {e!s}[/{UIStyles.ERROR}]"
            )
            return False

    def reject_change(self, change_id: str) -> bool:
        """Reject a pending change without modifying the file.

        Args:
            change_id: Change identifier.

        Returns:
            True if the change was found and rejected.
        """
        if change_id not in self.pending_changes:
            return False

        change = self.pending_changes[change_id]
        file_path = change["file_path"]

        change["state"] = ApplyState.CLOSED
        change["rejected_at"] = time.time()
        self.rejected_changes[change_id] = change
        del self.pending_changes[change_id]

        # Add to history
        self.change_history.append(
            {
                "change_id": change_id,
                "file_path": file_path,
                "action": "rejected",
                "timestamp": time.time(),
                "description": change.get("description"),
            }
        )

        console.print(
            f"[{UIStyles.WARNING}]{UIIcons.CANCEL} Changes rejected for {file_path}[/{UIStyles.WARNING}]"
        )
        return True

    def get_change(self, change_id: str) -> Optional[dict]:
        """Look up a change by ID across all three state dicts.

        Args:
            change_id: Change identifier.

        Returns:
            Change dict or None if not found.
        """
        if change_id in self.pending_changes:
            return self.pending_changes[change_id]
        if change_id in self.applied_changes:
            return self.applied_changes[change_id]
        if change_id in self.rejected_changes:
            return self.rejected_changes[change_id]
        return None

    def render_change_preview(self, change_id: str) -> Panel:
        """Render a side-by-side Rich diff preview for a change.

        Args:
            change_id: Change identifier.

        Returns:
            Rich Panel with current/proposed diff and confidence stats.
        """
        change = self.get_change(change_id)
        if not change:
            return Panel(
                Text("Change not found", style=UIStyles.ERROR),
                border_style=UIStyles.BORDER_ERROR,
            )

        file_path = change["file_path"]
        old_content = change["old_content"]
        new_content = change["new_content"]

        # Diff side-by-side
        old_panel = Panel(
            Syntax(old_content, "python", theme="monokai", line_numbers=True),
            title=f"[{UIStyles.ERROR}]Atual - {file_path}[/{UIStyles.ERROR}]",
            border_style=UIStyles.BORDER_ERROR,
            padding=(1, 2),
        )

        new_panel = Panel(
            Syntax(new_content, "python", theme="monokai", line_numbers=True),
            title=f"[{UIStyles.SUCCESS}]Proposto - {file_path}[/{UIStyles.SUCCESS}]",
            border_style=UIStyles.BORDER_SUCCESS,
            padding=(1, 2),
        )

        # Diff statistics
        diff_lines = list(
            difflib.unified_diff(
                old_content.splitlines(keepends=True),
                new_content.splitlines(keepends=True),
                fromfile="Current",
                tofile="Proposed",
                lineterm="",
            )
        )
        added = sum(
            1
            for line in diff_lines
            if line.startswith("+") and not line.startswith("+++")
        )
        removed = sum(
            1
            for line in diff_lines
            if line.startswith("-") and not line.startswith("---")
        )

        stats_text = Text()
        stats_text.append(f"+{added} -{removed} linhas", style=UIStyles.BODY)

        # Calculate heuristic confidence rating based on diff magnitude
        total_changes = added + removed
        if total_changes < 30:
            confidence = 98
            conf_style = UIStyles.SUCCESS
            risk_label = "Risco Baixo"
        elif total_changes < 150:
            confidence = 88
            conf_style = UIStyles.WARNING
            risk_label = "Risco Moderado"
        else:
            confidence = 72
            conf_style = UIStyles.ERROR
            risk_label = "Risco Elevado"

        stats_text.append("  │  Confiança: ", style=UIStyles.MUTED)
        stats_text.append(f"{confidence}%", style=f"bold {conf_style}")
        stats_text.append(f" ({risk_label})", style=f"dim {conf_style}")

        # Adapt preview layout based on terminal width
        from aura_cli.cli.ui.responsive import ResponsiveLayout

        layout_width = ResponsiveLayout(console).width
        if layout_width < 100:
            diff_display: Any = Group(old_panel, new_panel)
        else:
            diff_display = Columns([old_panel, new_panel], equal=True)

        return Panel(
            Group(diff_display, Text(), stats_text),
            title=f"Prévia da alteração - {change_id[:8]}  [ [y] aplicar  │  [n] rejeitar  │  [a] auto-run ]",
            border_style=UIStyles.BORDER_PRIMARY,
            padding=(1, 2),
        )

    def render_change_history(self, limit: int = 10) -> Table:
        """Render a Rich Table with the most recent change history.

        Args:
            limit: Maximum number of entries to display (default 10).

        Returns:
            Rich Table with timestamp, file, action and status columns.
        """
        table = Table(
            title="Histórico de alterações",
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            border_style=UIStyles.BORDER_PRIMARY,
        )

        table.add_column("Hora", width=12)
        table.add_column("Arquivo", width=25)
        table.add_column("Ação", width=10)
        table.add_column("Status", width=10)

        for entry in self.change_history[-limit:]:
            timestamp = datetime.fromtimestamp(entry["timestamp"]).strftime("%H:%M:%S")
            action = entry["action"]
            file_path = entry["file_path"]

            if action == "applied":
                action_icon = UIIcons.SUCCESS
                action_style = UIStyles.SUCCESS
                action_label = "Aplicado"
            else:
                action_icon = UIIcons.CANCEL
                action_style = UIStyles.WARNING
                action_label = "Rejeitado"

            table.add_row(
                f"[{UIStyles.MUTED}]{timestamp}[/]",
                f"[{UIStyles.PRIMARY}]{file_path}[/]",
                f"[{action_style}]{action_icon} {action_label}[/]",
                f"[{action_style}]Concluído[/]",
            )

        return table


_apply_reject_manager = ApplyRejectManager()


def get_apply_reject_manager() -> ApplyRejectManager:
    """Return the global apply/reject manager instance."""
    return _apply_reject_manager


def display_apply_reject_actions(
    change_id: str,
    file_path: str,
    can_apply: bool = True,
    can_reject: bool = True,
    on_apply: Optional[Callable] = None,
    on_reject: Optional[Callable] = None,
) -> None:
    """Render apply/reject toolbar actions for a pending change.

    Args:
        change_id: Change identifier.
        file_path: Target file path (for display purposes).
        can_apply: Show the apply action (default True).
        can_reject: Show the reject action (default True).
        on_apply: Custom callback; falls back to manager.apply_change.
        on_reject: Custom callback; falls back to manager.reject_change.
    """
    from aura_cli.cli.ui.toolbar import display_toolbar

    manager = get_apply_reject_manager()

    def handle_apply():
        """Handle apply action."""
        if on_apply:
            on_apply(change_id)
        else:
            manager.apply_change(change_id)

    def handle_reject():
        """Handle reject action."""
        if on_reject:
            on_reject(change_id)
        else:
            manager.reject_change(change_id)

    display_toolbar(
        tool_name="file_edit",
        can_copy=True,
        can_expand=False,
        can_run=False,
        can_apply=can_apply,
        can_reject=can_reject,
        has_output=False,
        on_copy=lambda: copy_code(
            (manager.get_change(change_id) or {}).get("new_content", "")
        ),
        on_apply=handle_apply,
        on_reject=handle_reject,
    )
