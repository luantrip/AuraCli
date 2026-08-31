"""Composition root for interactions between the CLI and Textual adapters."""

from __future__ import annotations

from typing import Any


def launch_textual_interface(app_loop: Any) -> None:
    """Run Textual with a bridge installed on the existing application loop."""
    from aura_cli.core.tools.human_intervention_adapter import (
        get_intervention_adapter,
    )
    from aura_cli.tui.app import AuraTUI
    from aura_cli.tui.bridge import TextualUIManager

    tui_app = AuraTUI(app_loop=app_loop)
    bridge = TextualUIManager(
        tui_app,
        status_queue=app_loop.ui.status_queue,
        stats=app_loop.stats,
        intervention_adapter_resolver=get_intervention_adapter,
    )
    original_ui = app_loop.ui
    app_loop.ui = bridge
    try:
        tui_app.run()
    finally:
        app_loop.ui = original_ui


async def open_diff_confirmation(
    ui: Any,
    *,
    file_path: str,
    diff_lines: list[str],
    new_content: str,
) -> str:
    """Open the Textual diff modal and return the selected action."""
    from aura_cli.tui.shell.screen_registry import ScreenId, open_screen_wait

    app = getattr(ui, "app", ui)
    action, _ = await open_screen_wait(
        app,
        ScreenId.DIFF_CONFIRM,
        file_path=file_path,
        diff_lines=diff_lines,
        new_content=new_content,
    )
    return action
