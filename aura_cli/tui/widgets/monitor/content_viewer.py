"""Main content viewing area for the monitor tool."""

from __future__ import annotations

from rich.syntax import Syntax as RichSyntax
from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.reactive import reactive
from textual.widgets import Markdown, Static

from aura_cli.application.presentation.monitor import (
    MonitorContentMode,
    build_content_view,
)


class ContentViewer(VerticalScroll):
    """Main content viewing area."""

    content = reactive("")
    content_type = reactive("text/plain")
    loading = reactive(False)
    error = reactive("")

    def compose(self) -> ComposeResult:
        yield Static("", id="content_area", classes="content-area")

    def watch_content(self, content: str) -> None:
        self._update_display()

    def watch_loading(self, loading: bool) -> None:
        self._update_display()

    def watch_error(self, error: str) -> None:
        self._update_display()

    def _update_display(self) -> None:
        try:
            self.remove_children()
            area = Static("", id="content_area", classes="content-area")

            view = build_content_view(
                self.content,
                self.content_type,
                loading=self.loading,
                error=self.error,
            )
            if view.mode is MonitorContentMode.LOADING:
                area.update(view.content)
                area.add_class("loading-message")
            elif view.mode is MonitorContentMode.ERROR:
                area.update(view.content)
                area.add_class("error-message")
            elif view.mode is MonitorContentMode.EMPTY:
                area.update(view.content)
                area.add_class("empty-message")
            else:
                if view.mode is MonitorContentMode.JSON:
                    try:
                        syntax = RichSyntax(
                            view.content, "json", theme="monokai", word_wrap=True
                        )
                        area.update(syntax)
                        self.mount(area)
                        return
                    except Exception:
                        area.update(view.content)
                elif view.mode is MonitorContentMode.MARKDOWN:
                    try:
                        markdown_widget = Markdown(view.content)
                        self.mount(markdown_widget)
                        return
                    except Exception:
                        area.update(view.content)
                else:
                    area.update(view.content)

            self.mount(area)
        except Exception as error:
            self.log.warning("Unable to render monitor content: %s", error)

    def set_content(self, content: str, content_type: str = "text/plain") -> None:
        self.content = content
        self.error = ""
        self.loading = False

    def set_error(self, error: str) -> None:
        self.error = error
        self.loading = False

    def set_loading(self, loading: bool) -> None:
        self.loading = loading
