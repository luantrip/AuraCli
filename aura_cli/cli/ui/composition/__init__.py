"""CLI UI composition — operational surfaces during AGI/Ops runs."""

from aura_cli.cli.ui.composition.dashboard_surface import (
    DASHBOARD_REGISTRY,
    render_dashboard_help,
    render_dashboard_subcommand,
)
from aura_cli.cli.ui.composition.operational_surface import (
    publish_agent_status,
    publish_status_renderable,
    publish_subagent_panel,
    publish_tool_execution_panel,
    publish_worker_feed_batch,
    publish_worker_feeds,
)
from aura_cli.cli.ui.composition.task_composite import render_task_composite_surface
from aura_cli.cli.ui.composition.visual_surface import VisualEmitter, surface_panel

__all__ = [
    "DASHBOARD_REGISTRY",
    "VisualEmitter",
    "publish_agent_status",
    "publish_status_renderable",
    "publish_subagent_panel",
    "publish_tool_execution_panel",
    "publish_worker_feed_batch",
    "publish_worker_feeds",
    "render_dashboard_help",
    "render_dashboard_subcommand",
    "render_task_composite_surface",
    "surface_panel",
]
