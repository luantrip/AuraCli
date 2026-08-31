"""Classification of Rich CLI modules by visual responsibility."""

from __future__ import annotations

from aura_cli.application.presentation.cli_visual import SurfaceRole

SURFACE_MODULES = {
    "rendering": SurfaceRole.FLOW,
    "components.message_bubble": SurfaceRole.FLOW,
    "components.agent_workspace": SurfaceRole.FLOW,
    "components.worker_feed": SurfaceRole.FLOW,
    "components.subagent_panel": SurfaceRole.FLOW,
    "components.confirmation": SurfaceRole.DECISION,
    "components.human_confirmation_dialog": SurfaceRole.DECISION,
    "components.error_display": SurfaceRole.DECISION,
    "apply_reject": SurfaceRole.DECISION,
    "console_view": SurfaceRole.INSPECT,
    "live_dashboard": SurfaceRole.INSPECT,
    "components.interactive_dashboard": SurfaceRole.INSPECT,
    "advanced.agent_dashboard": SurfaceRole.OPTIONAL,
    "tools.tool_history": SurfaceRole.OPTIONAL,
    "components.tool_execution_panel": SurfaceRole.LEGACY,
}

# Composition roots and injectable constructors may create Console. Render-time
# leaf adapters must use display_facade.get_console instead.
CONSOLE_FACTORY_ALLOWLIST = {
    "display_facade.py",
    "manager.py",
    "responsive.py",
    "accessibility.py",
    "loading_states.py",
    "live_dashboard.py",
    "chat/chat_renderer.py",
    "components/animated_spinner.py",
    "components/interactive_dashboard.py",
    "components/streaming_renderer.py",
    "components/toast.py",
}

__all__ = ["CONSOLE_FACTORY_ALLOWLIST", "SURFACE_MODULES"]
