from unittest.mock import MagicMock

import pytest

from aura_cli.tui.app import AuraTUI


@pytest.mark.asyncio
async def test_compact_viewport_uses_low_chrome_and_keeps_composer() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(72, 23)) as pilot:
        await pilot.pause()

        grid = app.query_one("#main_grid")
        footer = app.query_one("#footer")
        main_input = app.query_one("#main_input")
        task_panel = app.query_one("#todo_panel")

        assert grid.has_class("density-compact")
        assert footer.has_class("compact")
        assert main_input.display
        assert task_panel.display is False
        assert all(not title.display for title in app.query(".panel-title"))


@pytest.mark.asyncio
async def test_spacious_viewport_keeps_header_and_footer_details() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()

        grid = app.query_one("#main_grid")
        footer = app.query_one("#footer")

        assert grid.has_class("density-spacious")
        assert not footer.has_class("compact")
        assert all(title.display for title in app.query(".panel-title"))
