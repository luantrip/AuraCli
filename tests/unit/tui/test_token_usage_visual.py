from unittest.mock import MagicMock

import pytest
from textual.containers import Container

from aura_cli.tui.app import AuraTUI
from aura_cli.tui.screens.token_usage_screen import TokenUsageScreen


def test_token_usage_uses_one_shared_outer_frame() -> None:
    css = TokenUsageScreen.DEFAULT_CSS

    assert TokenUsageScreen.MODAL_ROOT_ID == "token_usage_modal"
    assert "border: thick" not in css
    assert "TokenUsageScreen #token_usage_modal" in css
    assert "border: round $primary" in css
    assert "TokenUsageScreen #token_usage_dialog" in css
    assert "border: none" in css


@pytest.mark.asyncio
async def test_token_usage_mounts_as_one_compact_frame() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        app.action_show_token_usage()
        await pilot.pause()

        root = app.screen.query_one("#token_usage_modal", Container)
        content = app.screen.query_one("#token_usage_dialog", Container)

        assert root.region.width == 68
        assert content.region.width < root.region.width
        assert content.styles.border.top[0] in {"", "none"}
        assert content.styles.padding.top == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["escape", "enter", "left"])
async def test_token_usage_closes_with_documented_keys_and_restores_composer(
    key: str,
) -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(160, 40)) as pilot:
        await pilot.pause()
        app.action_show_token_usage()
        await pilot.pause()

        assert isinstance(app.screen, TokenUsageScreen)
        await pilot.press(key)
        await pilot.pause()

        assert not isinstance(app.screen, TokenUsageScreen)
        assert app.focused is app.query_one("#main_input")


def test_token_usage_content_does_not_repeat_modal_title() -> None:
    screen = TokenUsageScreen()

    content = screen._build_content().plain

    assert not content.startswith("Context")
    assert "0.0k / 500k tokens" in content
    assert "Disponível" in content
    assert "Esc / Enter: fechar  |  ←: recolher" in content


def test_token_usage_clamps_negative_and_overflow_values() -> None:
    screen = TokenUsageScreen(used_tokens=600_000, total_tokens=500_000)

    content = screen._build_content().plain

    assert "600.0k / 500k tokens (100.00%)" in content
    assert content.count("◆") == 40

    screen = TokenUsageScreen(used_tokens=-10, total_tokens=-1)
    assert "0.0k / 0k tokens (0.00%)" in screen._build_content().plain
