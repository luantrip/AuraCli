"""Delegated task follow-up panel for Aura TUI."""

from dataclasses import dataclass
from typing import Optional

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Static

from aura_cli.tui.widgets.base import TimerWidget


@dataclass
class DelegationSnapshot:
    """Serializable delegated-task summary for the TUI."""

    summary: str
    latest_agi: str
    latest_ops: str
    details: str
    artifacts: str = ""


class DelegationPanel(TimerWidget):
    """Visual follow-up for delegated AGI/Ops tasks from the AppLoop."""

    def compose(self) -> ComposeResult:
        """Compose delegated-task monitor layout."""
        yield Static("Delegated Tasks", classes="pane-header")
        yield Static(
            "Backed by AppLoop delegated-task state and artifacts.",
            classes="field-help",
        )
        with Horizontal(classes="action-bar"):
            yield Button("⟳ Refresh", id="delegation_refresh_btn")
            yield Button("◈ Latest AGI", id="delegation_latest_agi_btn")
            yield Button("⚒ Latest Ops", id="delegation_latest_ops_btn")
            yield Button("◇ Artifacts", id="delegation_artifacts_btn")
            yield Button("◇ Snapshot", id="delegation_snapshot_btn")
            yield Button("◇ Reattach", id="delegation_reattach_btn")
        yield Static("", id="delegation_summary")
        yield VerticalScroll(
            Static("", id="delegation_details"), id="delegation_scroll"
        )

    def on_mount(self) -> None:
        """Load initial snapshot and keep it reasonably fresh."""
        self.refresh_panel()
        self.add_timer("refresh", 5.0, self.refresh_panel)

    def _get_app_loop(self):
        """Resolve AppLoop from the mounted TUI app."""
        return getattr(self.app, "app_loop", None)

    def _build_snapshot(self) -> DelegationSnapshot:
        """Collect delegated-task view data from AppLoop."""
        app_loop = self._get_app_loop()
        if not app_loop:
            return DelegationSnapshot(
                summary="AppLoop indisponível na TUI.",
                latest_agi="n/a",
                latest_ops="n/a",
                details="A TUI não recebeu um AppLoop ativo.",
                artifacts="n/a",
            )

        summary = app_loop.summarize_delegated_tasks()
        latest_agi = app_loop.get_latest_delegated_task("agi")
        latest_ops = app_loop.get_latest_delegated_task("ops")
        details = app_loop.list_delegated_tasks()
        artifacts = app_loop.get_delegated_task_artifacts()
        return DelegationSnapshot(
            summary=summary,
            latest_agi=latest_agi,
            latest_ops=latest_ops,
            details=details,
            artifacts=artifacts,
        )

    def refresh_panel(self) -> None:
        """Refresh delegated-task snapshot from AppLoop."""
        snapshot = self._build_snapshot()
        self.query_one("#delegation_summary", Static).update(
            f"{snapshot.summary}\n\nlatest_agi: {snapshot.latest_agi}\n\nlatest_ops: {snapshot.latest_ops}\n\nlatest_artifacts: {snapshot.artifacts}"
        )
        self.query_one("#delegation_details", Static).update(snapshot.details)

    def _preferred_agent_type(self) -> str:
        """Return the preferred delegated agent type for latest follow-up."""
        app_loop = self._get_app_loop()
        if not app_loop:
            return "agi"
        agi_latest = app_loop.get_latest_delegated_task("agi")
        return "agi" if agi_latest != "Nenhuma tarefa delegada encontrada." else "ops"

    def _show_latest(self, agent_type: str) -> None:
        """Show latest delegated task details for a given agent type."""
        app_loop = self._get_app_loop()
        if not app_loop:
            return
        details = app_loop.summarize_delegated_task(agent_type=agent_type)
        self.query_one("#delegation_details", Static).update(details)

    def _show_artifacts(self, agent_type: str = "") -> Optional[str]:
        """Show artifacts for the latest delegated task."""
        app_loop = self._get_app_loop()
        if not app_loop:
            return None
        resolved_agent_type = agent_type or self._preferred_agent_type()
        details = app_loop.get_delegated_task_artifacts(agent_type=resolved_agent_type)
        self.query_one("#delegation_details", Static).update(details)
        return details

    def _show_snapshot(self, agent_type: str = "") -> Optional[str]:
        """Show notebook snapshot for the latest delegated task."""
        app_loop = self._get_app_loop()
        if not app_loop:
            return None
        resolved_agent_type = agent_type or self._preferred_agent_type()
        details = app_loop.read_delegated_task_snapshot(agent_type=resolved_agent_type)
        self.query_one("#delegation_details", Static).update(details)
        return details

    def _reattach_latest(self) -> Optional[str]:
        """Reattach latest delegated context and return the resulting message."""
        app_loop = self._get_app_loop()
        if not app_loop:
            return None
        agent_type = self._preferred_agent_type()
        result = app_loop.reattach_delegated_task_context(agent_type=agent_type)
        self.query_one("#delegation_details", Static).update(result)
        return result

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle delegation panel button actions."""
        button_id = event.button.id
        if button_id == "delegation_refresh_btn":
            self.refresh_panel()
        elif button_id == "delegation_latest_agi_btn":
            self._show_latest("agi")
        elif button_id == "delegation_latest_ops_btn":
            self._show_latest("ops")
        elif button_id == "delegation_artifacts_btn":
            self._show_artifacts()
        elif button_id == "delegation_snapshot_btn":
            self._show_snapshot()
        elif button_id == "delegation_reattach_btn":
            result = self._reattach_latest()
            if result and hasattr(self.app, "post_message_to_chat"):
                self.app.post_message_to_chat("System", result)
