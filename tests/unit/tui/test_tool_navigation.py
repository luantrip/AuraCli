"""Shared navigation contracts for auxiliary TUI screens."""

from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Static

from aura_cli.tui.app import AuraTUI
from aura_cli.tui.screens import tools_menu_screen
from aura_cli.tui.shell.base_tool_screen import (
    pop_screen_and_restore_focus,
    restore_composer_focus,
)
from aura_cli.tui.tools import ToolAvailability


class ToolMenuHarness(App[None]):
    """Minimal host for the real launcher screen."""

    def compose(self) -> ComposeResult:
        yield Static("host")


def test_pop_screen_restores_focus_after_refresh_when_supported() -> None:
    restore_focus = Mock()
    app = SimpleNamespace(
        pop_screen=Mock(),
        _restore_composer_focus=restore_focus,
        call_after_refresh=Mock(),
    )

    pop_screen_and_restore_focus(app)

    app.pop_screen.assert_called_once_with()
    app.call_after_refresh.assert_called_once_with(restore_focus)
    restore_focus.assert_not_called()


def test_pop_screen_remains_compatible_without_focus_hook() -> None:
    app = SimpleNamespace(pop_screen=Mock())

    pop_screen_and_restore_focus(app)

    app.pop_screen.assert_called_once_with()


def test_restore_focus_uses_refresh_hook_when_available() -> None:
    restore_focus = Mock()
    app = SimpleNamespace(
        _restore_composer_focus=restore_focus,
        call_after_refresh=Mock(),
    )

    restore_composer_focus(app)

    app.call_after_refresh.assert_called_once_with(restore_focus)
    restore_focus.assert_not_called()


@pytest.mark.asyncio
async def test_tools_menu_layout_keeps_cards_and_hints_inside_viewport() -> None:
    app = AuraTUI(app_loop=Mock())
    with patch.object(
        tools_menu_screen,
        "get_tool_availability",
        return_value=ToolAvailability(True, False, False),
    ):
        async with app.run_test(size=(160, 40)) as pilot:
            app.push_screen(tools_menu_screen.ToolsMenuScreen())
            await pilot.pause()
            screen = app.screen
            cards = list(screen.query(".tool-card"))
            hints = list(screen.query(".action-key, .action-hint-text"))

            assert len(cards) == 5
            assert all(
                card.region.width > 0 and card.region.height > 0 for card in cards
            )
            assert all(
                card.region.x >= 0
                and card.region.y >= 0
                and card.region.x + card.region.width <= app.size.width
                and card.region.y + card.region.height <= app.size.height
                for card in cards
            )
            assert hints
            assert all(
                hint.region.x >= 0
                and hint.region.x + hint.region.width <= app.size.width
                for hint in hints
            )


@pytest.mark.asyncio
async def test_tools_menu_enter_restores_focus_before_tool_callback() -> None:
    app = ToolMenuHarness()
    with (
        patch.object(
            tools_menu_screen,
            "get_tool_availability",
            return_value=ToolAvailability(True, False, False),
        ),
        patch.object(
            tools_menu_screen, "pop_screen_and_restore_focus"
        ) as pop_and_restore,
        patch.object(app, "action_push_paint_screen", create=True) as launch,
    ):
        async with app.run_test() as pilot:
            app.push_screen(tools_menu_screen.ToolsMenuScreen())
            await pilot.pause()
            screen = app.screen
            screen.selected_index = 1
            screen.action_select_tool()

    pop_and_restore.assert_called_once_with(app)
    launch.assert_called_once_with()


@pytest.mark.asyncio
async def test_tools_menu_moves_one_cell_per_arrow() -> None:
    app = ToolMenuHarness()
    with patch.object(
        tools_menu_screen,
        "get_tool_availability",
        return_value=ToolAvailability(True, False, False),
    ):
        async with app.run_test() as pilot:
            app.push_screen(tools_menu_screen.ToolsMenuScreen())
            await pilot.pause()
            screen = app.screen

            assert isinstance(screen, tools_menu_screen.ToolsMenuScreen)
            assert screen.selected_index == 0
            assert app.focused is screen.query_one("#tool_card_0")
            await pilot.press("right")
            await pilot.pause()

            assert screen.selected_index == 1
            assert app.focused is screen.query_one("#tool_card_1")
