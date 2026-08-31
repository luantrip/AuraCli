"""Native TUI settings screen — composes decomposed widgets."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.containers import ScrollableContainer
from textual.widgets import Input, Select

from aura_cli.tui.shell.base_modal import BaseAuraModalScreen
from aura_cli.tui.widgets.settings.api_keys_section import ApiKeysSection
from aura_cli.tui.widgets.settings_panel import LLMSettingsPanel


class SettingsScreen(BaseAuraModalScreen[None]):
    """API keys section + LLM panel (shell base modal)."""

    TITLE = "⚙ Configurações"
    INITIAL_FOCUS_SELECTOR = "#provider_select"

    def compose_body(self) -> ComposeResult:
        yield ApiKeysSection(id="api_keys_section")
        with ScrollableContainer(id="llm_settings_scroll"):
            yield LLMSettingsPanel(id="llm_settings_panel")

    @on(LLMSettingsPanel.SettingsSaved)
    def _on_settings_saved(self, _event: LLMSettingsPanel.SettingsSaved) -> None:
        self.action_close_modal()

    @on(LLMSettingsPanel.SettingsReset)
    def _on_settings_reset(self, _event: LLMSettingsPanel.SettingsReset) -> None:
        self.action_close_modal()

    @on(ApiKeysSection.KeysChanged)
    def _on_keys_changed(self, event: ApiKeysSection.KeysChanged) -> None:
        if event.provider is None:
            panel = self.query_one("#llm_settings_panel", LLMSettingsPanel)
            panel.query_one("#api_key_input", Input).value = ""
            return
        panel = self.query_one("#llm_settings_panel", LLMSettingsPanel)
        provider_select = panel.query_one("#provider_select", Select)
        if str(provider_select.value) == event.provider:
            panel.query_one("#api_key_input", Input).value = ""
