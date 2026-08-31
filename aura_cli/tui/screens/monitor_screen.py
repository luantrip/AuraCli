"""Monitor Screen - auxiliary browser surface for Aura CLI."""

from __future__ import annotations

import contextlib
from typing import ClassVar

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical
from textual.widgets import Input

from aura_cli.application.presentation.monitor import build_address_view
from aura_cli.tui.shell.base_tool_screen import BaseToolScreen
from aura_cli.tui.tools.monitor import get_monitor_binary
from aura_cli.tui.tools.monitor.browser import BrowserState, BrowserTab, MonitorBrowser
from aura_cli.tui.widgets.monitor import (
    AddressBar,
    ContentViewer,
    MonitorStatusBar,
    MonitorUnavailablePanel,
    TabBar,
)


class MonitorScreen(BaseToolScreen):
    """Terminal browser with tabs, vim-style navigation, and shared tool chrome."""

    SCREEN_TITLE = "Monitor de Conteúdo"
    SCREEN_SUBTITLE = "Navegador web no terminal · Ctrl+M no chat"

    BINDINGS: ClassVar[list] = [
        *BaseToolScreen.BINDINGS,
        Binding("g", "goto", "Abrir URL", show=True),
        Binding("r", "reload", "Recarregar", show=True),
        Binding("b", "back", "Voltar"),
        Binding("f", "forward", "Avançar"),
        Binding("H", "home", "Início"),
        Binding("/", "search", "Pesquisar", show=True),
        Binding("j", "scroll_down", "Rolar para baixo"),
        Binding("k", "scroll_up", "Rolar para cima"),
        Binding("ctrl+d", "page_down", "Próxima página"),
        Binding("ctrl+u", "page_up", "Página anterior"),
        Binding("t", "new_tab", "Nova aba"),
        Binding("w", "close_tab", "Fechar aba"),
        Binding("1", "tab_1", "Aba 1", show=False),
        Binding("2", "tab_2", "Aba 2", show=False),
        Binding("3", "tab_3", "Aba 3", show=False),
    ]

    def __init__(self, initial_url: str = "about:blank", **kwargs):
        super().__init__(**kwargs)
        self._initial_url = initial_url
        self._browser = MonitorBrowser()
        self._browser.on_content_loaded(self._on_content_loaded)
        self._browser.on_error(self._on_error)
        self._browser.on_state_changed(self._on_state_changed)

    def _monitor_available(self) -> bool:
        """Return the current monitor availability for this screen."""
        return get_monitor_binary(refresh=True) is not None

    def compose_tool_body(self) -> ComposeResult:
        if not self._monitor_available():
            yield MonitorUnavailablePanel()
            return

        with Container(id="browser-container"):
            with Vertical():
                yield TabBar(
                    self._browser.state.tabs,
                    self._browser.state.active_tab_index,
                    id="tab_bar",
                )
                yield AddressBar(id="address_bar")
                yield ContentViewer(id="content_viewer")
                yield MonitorStatusBar(id="status_bar")

    def on_mount(self) -> None:
        if not self._monitor_available():
            return

        if self._initial_url and self._initial_url != "about:blank":
            self.run_worker(self._browser.goto(self._initial_url))
        else:
            viewer = self.query_one("#content_viewer", ContentViewer)
            viewer.set_content(self._welcome_content(), "text/markdown")

    def _welcome_content(self) -> str:
        return """
# Terminal Content Monitor

Bem-vindo ao Monitor da Aura CLI, um navegador web completo para o terminal.

## Quick Start
* Pressione **g** para abrir uma URL
* Pressione **r** para recarregar
* Pressione **/** para pesquisar
* Use **b** / **f** para voltar ou avançar

## Recursos
* **Navegar**: histórico e abas
* **Visualizar**: suporte a Markdown, HTML e JSON
* **Monitorar**: inspeção de endpoints
* **Abas**: várias páginas na mesma sessão

Experimente: [DuckDuckGo Lite](https://lite.duckduckgo.com)
"""

    def _on_content_loaded(self, tab: BrowserTab) -> None:
        if not self._monitor_available():
            return

        try:
            viewer = self.query_one("#content_viewer", ContentViewer)
            viewer.set_content(tab.content, tab.content_type.value)

            address = self.query_one("#address_bar", AddressBar)
            view = build_address_view(tab)
            address.url = view.url
            address.loading = view.loading
            address.can_back = view.can_back
            address.can_forward = view.can_forward

            status = self.query_one("#status_bar", MonitorStatusBar)
            status.message = view.status
        except Exception as error:
            self.log.warning("Unable to render monitor content: %s", error)

    def _on_error(self, error: str) -> None:
        if not self._monitor_available():
            return

        try:
            viewer = self.query_one("#content_viewer", ContentViewer)
            viewer.set_error(error)

            address = self.query_one("#address_bar", AddressBar)
            address.loading = False

            status = self.query_one("#status_bar", MonitorStatusBar)
            status.message = f"Erro: {error}"

        except Exception as render_error:
            self.log.warning("Unable to render monitor error: %s", render_error)

    def _on_state_changed(self, state: BrowserState) -> None:
        if not self._monitor_available():
            return

        try:
            tab_bar = self.query_one("#tab_bar", TabBar)
            tab_bar.update_tabs(state.tabs, state.active_tab_index)
        except Exception as error:
            self.log.warning("Unable to render monitor tabs: %s", error)

    def on_tab_bar_tab_selected(self, event: TabBar.TabSelected) -> None:
        self._browser.switch_tab(event.index)
        if tab := self._browser.current_tab:
            self._on_content_loaded(tab)

    def on_tab_bar_new_tab_requested(self, event: TabBar.NewTabRequested) -> None:
        self._browser.new_tab()

    def on_address_bar_url_submitted(self, event: AddressBar.UrlSubmitted) -> None:
        self._goto_url(event.url)

    def on_address_bar_navigation_action(
        self, event: AddressBar.NavigationAction
    ) -> None:
        actions = {
            "back": self.action_back,
            "forward": self.action_forward,
            "reload": self.action_reload,
            "home": self.action_home,
        }
        action = actions.get(event.action)
        if action:
            action()

    def _goto_url(self, url: str) -> None:
        if not self._monitor_available():
            return

        try:
            address = self.query_one("#address_bar", AddressBar)
            address.loading = True

            viewer = self.query_one("#content_viewer", ContentViewer)
            viewer.set_loading(True)

            status = self.query_one("#status_bar", MonitorStatusBar)
            status.message = f"Carregando {url}..."
        except Exception as error:
            self.log.warning("Unable to render monitor loading state: %s", error)

        self.run_worker(self._browser.goto(url))

    def action_goto(self) -> None:
        if not self._monitor_available():
            return
        try:
            url_input = self.query_one("#url_input", Input)
            url_input.focus()
            url_input.value = ""
        except Exception as error:
            self.log.warning("Unable to focus monitor address: %s", error)

    def action_reload(self) -> None:
        if not self._monitor_available():
            return
        self.run_worker(self._browser.reload())

    def action_back(self) -> None:
        if not self._monitor_available():
            return
        self.run_worker(self._browser.go_back())

    def action_forward(self) -> None:
        if not self._monitor_available():
            return
        self.run_worker(self._browser.go_forward())

    def action_home(self) -> None:
        if not self._monitor_available():
            return
        self._goto_url("about:blank")

    def action_search(self) -> None:
        if not self._monitor_available():
            return
        with contextlib.suppress(Exception):
            address = self.query_one("#address_bar", AddressBar)
            address.query_one("#url_input", Input).focus()

    def action_scroll_down(self) -> None:
        if not self._monitor_available():
            return
        with contextlib.suppress(Exception):
            self.query_one("#content_viewer", ContentViewer).scroll_down()

    def action_scroll_up(self) -> None:
        if not self._monitor_available():
            return
        with contextlib.suppress(Exception):
            self.query_one("#content_viewer", ContentViewer).scroll_up()

    def action_page_down(self) -> None:
        if not self._monitor_available():
            return
        with contextlib.suppress(Exception):
            self.query_one("#content_viewer", ContentViewer).scroll_page_down()

    def action_page_up(self) -> None:
        if not self._monitor_available():
            return
        with contextlib.suppress(Exception):
            self.query_one("#content_viewer", ContentViewer).scroll_page_up()

    def action_new_tab(self) -> None:
        if not self._monitor_available():
            return
        self._browser.new_tab()

    def action_close_tab(self) -> None:
        if not self._monitor_available():
            return
        self._browser.close_tab()

    def action_tab_1(self) -> None:
        self._browser.switch_tab(0)

    def action_tab_2(self) -> None:
        self._browser.switch_tab(1)

    def action_tab_3(self) -> None:
        self._browser.switch_tab(2)
