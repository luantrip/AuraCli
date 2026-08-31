"""Initial focus contracts for modal TUI screens."""

from unittest.mock import patch

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Select, Static

from aura_cli.application.presentation.llm_settings import LLMSettings
from aura_cli.tui.screens.constitution_screen import ConstitutionScreen
from aura_cli.tui.screens.settings_screen import SettingsScreen
from aura_cli.tui.widgets.settings.api_keys_section import ApiKeysSection
from aura_cli.tui.widgets.settings_panel import LLMSettingsPanel


class ModalFocusHarness(App[None]):
    """Minimal host for modal focus contracts."""

    def compose(self) -> ComposeResult:
        yield Static("composer", id="composer")


@pytest.mark.asyncio
async def test_settings_modal_focuses_provider_select_after_mount() -> None:
    app = ModalFocusHarness()
    settings = LLMSettings()
    with (
        patch.object(
            LLMSettingsPanel, "_load_settings_from_config", return_value=settings
        ),
        patch.object(ApiKeysSection, "refresh_status"),
    ):
        async with app.run_test(size=(120, 40)) as pilot:
            app.push_screen(SettingsScreen())
            await pilot.pause()
            await pilot.pause()

            screen = app.screen
            assert app.focused is screen.query_one("#provider_select", Select)


@pytest.mark.asyncio
async def test_constitution_modal_focuses_visible_stage_select_after_mount() -> None:
    app = ModalFocusHarness()
    async with app.run_test(size=(120, 40)) as pilot:
        app.push_screen(ConstitutionScreen())
        await pilot.pause()
        await pilot.pause()

        screen = app.screen
        assert app.focused is screen.query_one("#stage-select", Select)
