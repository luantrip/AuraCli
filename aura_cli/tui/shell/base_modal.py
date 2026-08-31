"""Base classes for Aura full-screen modal screens (Textual ModalScreen stack)."""

from __future__ import annotations

from typing import ClassVar, Generic, TypeVar

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.css.query import NoMatches
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from aura_cli.tui.shell.base_tool_screen import restore_composer_focus

T = TypeVar("T")


class BaseAuraModalScreen(ModalScreen[T], Generic[T]):
    """
    Decomposed modal layout: header + body (override) + optional footer.

    Subclasses implement ``compose_body()``; header/footer stay consistent.
    Dismiss with ``self.dismiss(value)`` using type ``T``.
    """

    TITLE: ClassVar[str] = ""
    SHOW_FOOTER_CLOSE: ClassVar[bool] = True
    FOOTER_CLOSE_LABEL: ClassVar[str] = "Fechar"
    MODAL_ROOT_ID: ClassVar[str] = "aura_modal_root"
    INITIAL_FOCUS_SELECTOR: ClassVar[str | None] = None

    BINDINGS: ClassVar[list] = [
        Binding("escape", "close_modal", "Fechar", show=True),
    ]

    def on_mount(self) -> None:
        """Focus the first useful control after the modal layout is ready."""
        self.call_after_refresh(self._focus_initial_control)

    def _focus_initial_control(self) -> None:
        """Focus an explicit selector or the first enabled form control."""
        target = None
        if self.INITIAL_FOCUS_SELECTOR:
            try:
                target = self.query_one(self.INITIAL_FOCUS_SELECTOR)
            except NoMatches:
                return
        else:
            target = next(
                (
                    widget
                    for widget in self.query("Input, Select, Button, Switch")
                    if widget.can_focus and not widget.disabled
                ),
                None,
            )
        if target is not None and target.can_focus and not target.disabled:
            target.focus()

    def compose(self) -> ComposeResult:
        with Container(id=self.MODAL_ROOT_ID, classes="aura-modal-root"):
            if self.TITLE:
                yield Static(self.TITLE, classes="settings-header aura-modal-title")
            yield from self.compose_body()
            if self.SHOW_FOOTER_CLOSE:
                with Horizontal(classes="button-row aura-modal-footer"):
                    yield Button(
                        self.FOOTER_CLOSE_LABEL,
                        id="aura_modal_close",
                        variant="default",
                    )

    def compose_body(self) -> ComposeResult:
        """Override with modal content."""
        yield Static("")

    def action_close_modal(self) -> None:
        self._dismiss_and_restore_focus(self._default_dismiss_value())

    def _dismiss_and_restore_focus(self, value: T) -> None:
        """Dismiss this modal and return focus to the primary composer."""
        app = self.app
        self.dismiss(value)
        restore_composer_focus(app)

    def _default_dismiss_value(self) -> T:
        """Override when ``T`` is not ``None`` and ESC should return a sentinel."""
        return None  # type: ignore[return-value]

    @on(Button.Pressed, "#aura_modal_close")
    def _on_modal_close_pressed(self) -> None:
        self.action_close_modal()


class BaseAuraResultModalScreen(BaseAuraModalScreen[T], Generic[T]):
    """Modal without default footer; subclass handles dismiss via actions."""

    SHOW_FOOTER_CLOSE = False
