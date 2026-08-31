from unittest.mock import MagicMock

import pytest
from textual.widgets import Input

from aura_cli.tui.app import AuraTUI
from aura_cli.tui.widgets.command_palette import CommandPalette


@pytest.mark.asyncio
async def test_command_palette_action_opens_overlay_and_focuses_search() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(120, 32)) as pilot:
        await pilot.pause()
        palette = app.query_one("#command_palette", CommandPalette)
        assert not palette.is_visible

        app.action_toggle_command_palette()
        await pilot.pause()

        assert palette.is_visible
        assert palette.has_class("-visible")
        assert app.focused is palette.query_one("#palette_search", Input)

        app.action_toggle_command_palette()
        await pilot.pause()

        assert not palette.is_visible
        assert app.focused is app.query_one("#main_input")
