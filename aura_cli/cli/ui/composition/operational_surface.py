"""Composition layer for CLI operational rendering (tools, sub-agents, workers)."""

from __future__ import annotations

from typing import Any, List, Literal

from rich.console import RenderableType

AgentKind = Literal["agi", "ops", "tester"]

_AGENT_PREFIX: dict[AgentKind, str] = {
    "agi": "[Aura AGI]",
    "ops": "[Aura Ops]",
    "tester": "[TesterWorker]",
}


def publish_agent_status(
    status_queue: Any,
    agent: AgentKind,
    message: str,
) -> None:
    """Enqueue a normalized agent status line (parsed as WorkerActivityFeed)."""
    if status_queue is None or not message:
        return
    prefix = _AGENT_PREFIX.get(agent, _AGENT_PREFIX["agi"])
    status_queue.put(f"› {prefix} {message.strip()}")


def publish_worker_feed_batch(status_queue: Any, messages: List[Any]) -> None:
    """Parse a batch of status messages and publish one combined feed renderable."""
    if status_queue is None or not messages:
        return
    from aura_cli.cli.ui.components.worker_feed import parse_status_messages

    feeds = parse_status_messages(messages)
    if feeds:
        publish_worker_feeds(status_queue, feeds)


def publish_status_renderable(
    status_queue: Any,
    renderable: RenderableType,
    *,
    sender: str = "system",
) -> None:
    """Push a Rich renderable to the worker status queue (UI thread consumes)."""
    if status_queue is None:
        return
    status_queue.put(
        {
            "type": "chat_message",
            "sender": sender,
            "content": renderable,
        }
    )


def publish_subagent_panel(status_queue: Any, panel: Any) -> None:
    """Refresh SubAgentPanel in the CLI event loop."""
    if panel is None or status_queue is None:
        return
    publish_status_renderable(status_queue, panel.render())


def publish_tool_execution_panel(panel: Any = None) -> None:
    """Display grouped tool panel (wraps tool_execution_panel.display_tool_panel)."""
    from aura_cli.cli.ui.components.tool_execution_panel import display_tool_panel

    display_tool_panel(panel)


def publish_worker_feeds(status_queue: Any, feeds: Any) -> None:
    """Publish WorkerActivityFeed group renderable."""
    if feeds is None or status_queue is None:
        return
    from aura_cli.cli.ui.components.worker_feed import render_worker_feeds

    publish_status_renderable(status_queue, render_worker_feeds(feeds))
