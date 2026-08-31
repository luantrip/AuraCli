"""Status Sidebar Widget for Aura TUI.

Sidebar displaying system stats and active AGI tasks with tree visualization.
"""

import hashlib
import json

from textual.containers import Vertical
from textual.widgets import Static, Tree

from aura_cli.core.config import get_config_manager
import aura_cli.tui.constants as tui_constants
from aura_cli.tui.widgets.metrics_panel import MetricsPanel


class AuraStatusSidebar(Vertical):
    """Sidebar displaying System Stats and Active AGI Tasks.

    Features:
    - System status header with Aura branding
    - MetricsPanel integration for comprehensive stats
    - Active tasks tree view with status icons
    - Real-time updates (incremental — only rebuilds when state changes)
    - Collapsible sections
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Fingerprint of the last rendered task_states — avoids full
        # rebuild and the visible flicker it causes when nothing changed.
        self._last_tree_hash: str = ""

    def compose(self):
        """Compose sidebar structure."""
        yield Static(
            f"{tui_constants.get_glyph('AURA_STAR')} AURA SYSTEM",
            classes="status-header",
        )
        yield MetricsPanel(id="metrics_panel")
        yield Static(
            f"\n{tui_constants.get_glyph('AGI')} ACTIVE TASKS",
            classes="status-header",
        )
        yield Tree("Tasks", id="task_tree")

    def update_stats(self, stats: dict) -> None:
        """Update the metrics panel with real data."""
        metrics_panel = self.query_one("#metrics_panel", MetricsPanel)

        display_metrics = {
            "Status": stats.get("status", "idle").upper(),
            "Mode": stats.get("mode", "Interactive"),
            "Files Read": stats.get("files_read", 0),
            "Files Edited": stats.get("files_edited", 0),
            "Files Created": stats.get("files_created", 0),
            "LLM Calls": stats.get("llm_calls", 0),
            "Tool Calls": stats.get("tool_calls", 0),
            "Total Tokens": stats.get("total_tokens", 0),
            "Exec Time": stats.get("total_execution_time", "0.00s"),
            "Nim Engine": self._get_nim_status(),
        }

        metrics_panel.update_metrics(display_metrics)

    def _get_nim_status(self) -> str:
        """Check if Nim is configured."""
        try:
            config = get_config_manager()
            # Compatible with new schema via ConfigCompat
            nim_path = config.get("nim_binary_path")
            if nim_path and "mock" not in str(nim_path).lower():
                return "PRONTO"
            return "NÃO CONFIGURADO"
        except Exception:
            return "ERRO"

    def update_task_tree(self, task_states: dict) -> None:
        """Update the tree widget with current tasks and subtasks.

        Uses the icon embedded in each node label for status styling because
        Textual's TreeNode does not expose add_class/set_class directly.
        The icon itself provides the semantic colour cue without CSS classes.

        Rebuilds only when the incoming state has actually changed (fingerprint
        comparison) to avoid the visible flicker caused by clear() + full
        repopulation on every polling cycle.
        """
        # Fingerprint — cheap serialisation of only the fields we display.
        try:
            fingerprint = hashlib.md5(
                json.dumps(task_states, sort_keys=True, default=str).encode(),
                usedforsecurity=False,
            ).hexdigest()
        except Exception:
            fingerprint = ""

        if fingerprint and fingerprint == self._last_tree_hash:
            return  # nothing changed — skip rebuild
        self._last_tree_hash = fingerprint

        tree_widget = self.query_one("#task_tree", Tree)
        tree_widget.clear()

        root = tree_widget.root

        if not task_states:
            root.label = "Sem Tarefas Ativas"
            root.data = None
            root.expand()
            return

        root.label = "Tarefas Ativas"
        root.data = None
        root.expand()

        for task_id, task_data in task_states.items():
            task_status = task_data.get("status", "pending")
            task_status_icon = tui_constants.STATUS_ICONS.get(
                task_status, tui_constants.get_glyph("IDLE", "[ ]")
            )
            task_name = task_data.get("name", "Unnamed Task")

            task_node = root.add(
                f"{task_status_icon} {task_name}",
                data={"task_id": task_id, "type": "task", "status": task_status},
            )
            task_node.expand()

            for subtask_id, subtask_data in task_data.get("children", {}).items():
                subtask_status = subtask_data.get("status", "pending")
                subtask_status_icon = tui_constants.STATUS_ICONS.get(
                    subtask_status,
                    tui_constants.get_glyph("IDLE", "[ ]"),
                )
                subtask_name = subtask_data.get("name", "Unnamed Subtask")

                task_node.add(
                    f"{subtask_status_icon} {subtask_name}",
                    data={
                        "task_id": subtask_id,
                        "type": "subtask",
                        "status": subtask_status,
                    },
                )
