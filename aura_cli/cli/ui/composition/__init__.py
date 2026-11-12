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
    publish_worker_feed_batch,
    publish_worker_feeds,
)
from aura_cli.cli.ui.composition.visual_surface import VisualEmitter, surface_panel

__all__ = [
    "DASHBOARD_REGISTRY",
    "VisualEmitter",
    "publish_agent_status",
    "publish_status_renderable",
    "publish_subagent_panel",
    "publish_worker_feed_batch",
    "publish_worker_feeds",
    "render_dashboard_help",
    "render_dashboard_subcommand",
    "surface_panel",
]
