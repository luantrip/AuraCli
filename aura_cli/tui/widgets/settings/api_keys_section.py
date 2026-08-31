"""API key management block for settings (composable widget)."""

from __future__ import annotations

from typing import Callable, Optional

from textual import on
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Select, Static

from aura_cli.core.api_key_store import (
    API_PROVIDERS,
    clear_all_api_keys,
    clear_api_key_for_provider,
    format_providers_status,
    set_api_key_for_provider,
)
from aura_cli.tui.shell.prompts import push_confirm, push_input


class ApiKeysSection(Static):
    """Provider key status + add / remove / clear-all actions."""

    class KeysChanged(Message):
        """Posted after any key mutation."""

        def __init__(self, provider: Optional[str] = None) -> None:
            super().__init__()
            self.provider = provider

    def __init__(
        self,
        *,
        on_keys_changed: Optional[Callable[[Optional[str]], None]] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._on_keys_changed = on_keys_changed

    def compose(self) -> ComposeResult:
        with Vertical(classes="settings-section"):
            yield Static("Chaves de API", classes="section-title")
            yield Static("", id="api_keys_status")
            with Horizontal(classes="field-row"):
                yield Select(
                    [(label, pid) for pid, label, _ in API_PROVIDERS],
                    id="api_provider_select",
                )
                yield Button(
                    "Adicionar / atualizar",
                    id="api_set_btn",
                    variant="primary",
                )
                yield Button("Remover", id="api_remove_btn", variant="error")
                yield Button(
                    "Limpar todas",
                    id="api_clear_all_btn",
                    variant="warning",
                )

    def on_mount(self) -> None:
        self.refresh_status()

    def refresh_status(self) -> None:
        self.query_one("#api_keys_status", Static).update(format_providers_status())

    def _notify_changed(self, provider: Optional[str] = None) -> None:
        self.refresh_status()
        self.post_message(self.KeysChanged(provider))
        if self._on_keys_changed:
            self._on_keys_changed(provider)

    def _selected_provider(self) -> tuple[str, str]:
        select = self.query_one("#api_provider_select", Select)
        provider = str(select.value)
        label = next((n for p, n, _ in API_PROVIDERS if p == provider), provider)
        return provider, label

    @on(Button.Pressed, "#api_set_btn")
    def _on_set_key(self) -> None:
        provider, label = self._selected_provider()

        def _on_key(value: str | None) -> None:
            if value:
                set_api_key_for_provider(provider, value)
                self.notify(f"Chave salva: {label}", title="API Key")
                self._notify_changed(provider)

        push_input(
            self.app,
            title=f"Chave API — {label}",
            message="Cole a chave do provedor:",
            password=True,
            on_result=_on_key,
        )

    @on(Button.Pressed, "#api_remove_btn")
    def _on_remove_key(self) -> None:
        provider, label = self._selected_provider()

        def _on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                clear_api_key_for_provider(provider)
                self.notify(f"Chave removida: {label}", title="API Key")
                self._notify_changed(provider)

        push_confirm(
            self.app,
            title="Remover chave",
            message=f"Remover a chave de {label}?",
            dangerous=True,
            confirm_label="Remover",
            on_result=_on_confirm,
        )

    @on(Button.Pressed, "#api_clear_all_btn")
    def _on_clear_all(self) -> None:
        def _on_confirm(confirmed: bool | None) -> None:
            if confirmed:
                clear_all_api_keys()
                self.notify("Todas as chaves foram removidas", title="API Key")
                self._notify_changed(None)

        push_confirm(
            self.app,
            title="Limpar todas as chaves",
            message="Remover TODAS as chaves de API? Esta ação não pode ser desfeita.",
            dangerous=True,
            confirm_label="Limpar tudo",
            on_result=_on_confirm,
        )
