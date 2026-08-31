"""
Optional advanced agent dashboard components for the CLI.

This module is intentionally narrow. The canonical CLI experience lives in the
chat and operational feedback surfaces; this file only exposes an opt-in
overview widget for agent orchestration state.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, List, Optional, Tuple

from rich.console import Console, Group, RenderableType
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from aura_cli.cli.ui.constants import UIIcons, UIStyles


class AgentStatus(Enum):
    """Status de um agente."""

    IDLE = "idle"
    THINKING = "thinking"
    EXECUTING = "executing"
    COMMUNICATING = "communicating"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


_AGENT_STATUS_LABELS = {
    AgentStatus.IDLE: "ocioso",
    AgentStatus.THINKING: "pensando",
    AgentStatus.EXECUTING: "executando",
    AgentStatus.COMMUNICATING: "comunicando",
    AgentStatus.WAITING: "aguardando",
    AgentStatus.ERROR: "erro",
    AgentStatus.COMPLETED: "concluído",
}


@dataclass
class AgentState:
    """Snapshot compacto do estado de um agente."""

    agent_id: str
    name: str
    type: str
    status: AgentStatus
    current_task: Optional[str] = None
    messages_sent: int = 0
    messages_received: int = 0
    memory_entries: int = 0
    tasks_completed: int = 0
    execution_time: float = 0.0
    last_activity: Optional[datetime] = None


class AgentOrchestrationView:
    """Rich view for the agent orchestration dashboard."""

    def __init__(self, orchestrator: Optional[Any] = None):
        self.orchestrator = orchestrator

    def get_agent_states(self) -> List[AgentState]:
        """Get estados reais de todos os agentes do orchestrator"""
        if not self.orchestrator or not hasattr(self.orchestrator, "agents"):
            return []

        states: List[AgentState] = []
        for agent_id, agent in self.orchestrator.agents.items():
            states.append(
                AgentState(
                    agent_id=agent_id,
                    name=getattr(agent, "name", agent_id),
                    type=getattr(agent, "agent_type", "unknown"),
                    status=self._map_agent_status(agent),
                    current_task=getattr(agent, "current_task", None),
                    messages_sent=getattr(agent, "messages_sent", 0),
                    messages_received=getattr(agent, "messages_received", 0),
                    memory_entries=getattr(agent, "memory_entries", 0),
                    tasks_completed=getattr(agent, "tasks_completed", 0),
                    execution_time=getattr(agent, "total_execution_time", 0.0),
                    last_activity=getattr(agent, "last_activity", None),
                )
            )

        return states

    def _map_agent_status(self, agent: Any) -> AgentStatus:
        """Map an agent status string to a display label."""
        if not hasattr(agent, "status"):
            return AgentStatus.IDLE

        status_map = {
            "idle": AgentStatus.IDLE,
            "thinking": AgentStatus.THINKING,
            "executing": AgentStatus.EXECUTING,
            "working": AgentStatus.EXECUTING,
            "communicating": AgentStatus.COMMUNICATING,
            "waiting": AgentStatus.WAITING,
            "error": AgentStatus.ERROR,
            "completed": AgentStatus.COMPLETED,
        }

        raw_status = getattr(agent, "status", "idle")
        status = getattr(raw_status, "value", raw_status)
        status = str(status).lower()
        return status_map.get(status, AgentStatus.IDLE)

    def _get_status_icon_and_style(self, status: AgentStatus) -> Tuple[str, str]:
        """Return icon and Rich style for an agent status."""
        status_map = {
            AgentStatus.IDLE: (UIIcons.IDLE, UIStyles.MUTED),
            AgentStatus.THINKING: (UIIcons.THINKING, UIStyles.INFO),
            AgentStatus.EXECUTING: (UIIcons.WORKING, UIStyles.PRIMARY),
            AgentStatus.COMMUNICATING: ("📡", UIStyles.ACCENT),
            AgentStatus.WAITING: (UIIcons.LOADING, UIStyles.WARNING),
            AgentStatus.ERROR: (UIIcons.ERROR, UIStyles.ERROR),
            AgentStatus.COMPLETED: (UIIcons.SUCCESS, UIStyles.SUCCESS),
        }
        return status_map.get(status, (UIIcons.IDLE, UIStyles.MUTED))

    def _render_empty_state(self) -> RenderableType:
        """Render the empty state panel."""
        body = Text()
        body.append(
            "Nenhum orchestrator ativo foi conectado a esta view.\n",
            style=UIStyles.BODY,
        )
        body.append(
            "Use o chat principal e a trilha operacional como superfície canônica.\n",
            style=UIStyles.MUTED,
        )
        body.append(
            "Este dashboard é um explorador opcional de estado.", style=UIStyles.MUTED
        )
        return Panel(
            body,
            title=f"{UIIcons.AGENT} Orquestração de agentes (opcional)",
            title_align="left",
            border_style=UIStyles.BORDER_PRIMARY,
            padding=(1, 2),
        )

    def render(self, console: Console) -> RenderableType:
        """Render the agent orchestration view."""
        states = self.get_agent_states()
        if not states:
            return self._render_empty_state()

        table = Table(
            title=f"{UIIcons.AGENT} Orquestração de agentes (opcional)",
            title_style=UIStyles.TITLE,
            show_header=True,
            header_style=UIStyles.SUBTITLE,
            border_style=UIStyles.BORDER_PRIMARY,
            expand=False,
        )
        table.add_column("Agente", style=UIStyles.LABEL, width=20)
        table.add_column("Status", style=UIStyles.INFO, width=12)
        table.add_column("Tarefa atual", style=UIStyles.BODY, width=30)
        table.add_column("Msgs", justify="center", width=8)
        table.add_column("Memória", justify="center", width=8)
        table.add_column("Tarefas", justify="center", width=8)
        table.add_column("Tempo", justify="right", width=10)

        for state in states:
            icon, style = self._get_status_icon_and_style(state.status)

            agent_name = Text()
            agent_name.append(f"{state.name}\n", style=UIStyles.LABEL)
            agent_name.append(f"({state.type})", style=UIStyles.MUTED)

            status_text = Text()
            status_text.append(f"{icon} ", style=style)
            status_text.append(_AGENT_STATUS_LABELS[state.status], style=style)

            current_task = state.current_task or "—"
            if len(current_task) > 28:
                current_task = current_task[:25] + "..."

            table.add_row(
                agent_name,
                status_text,
                current_task,
                f"{state.messages_sent}/{state.messages_received}",
                str(state.memory_entries),
                str(state.tasks_completed),
                f"{state.execution_time:.1f}s",
            )

        total_agents = len(states)
        active_agents = sum(
            1
            for state in states
            if state.status not in [AgentStatus.IDLE, AgentStatus.COMPLETED]
        )
        total_messages = sum(
            state.messages_sent + state.messages_received for state in states
        )

        stats_text = Text()
        stats_text.append(f"{UIIcons.INFO} ", style=UIStyles.INFO)
        stats_text.append("Total: ", style=UIStyles.LABEL)
        stats_text.append(f"{total_agents} ", style=UIStyles.PRIMARY)
        stats_text.append("| Ativos: ", style=UIStyles.LABEL)
        stats_text.append(f"{active_agents} ", style=UIStyles.SUCCESS)
        stats_text.append("| Mensagens: ", style=UIStyles.LABEL)
        stats_text.append(f"{total_messages}", style=UIStyles.ACCENT)

        return Group(table, stats_text)
