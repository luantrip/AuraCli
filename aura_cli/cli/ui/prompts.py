"""Single interactive-prompt layer for the CLI (P1-3).

Onboarding used ``questionary`` while ``/settings`` used stock ``prompt_toolkit``
dialogs, and the two disagree on the most basic gesture: in a stock
``radiolist_dialog`` ``Enter`` only *marks* an option and the user still has to
``Tab`` to the OK button and press ``Enter`` again (``input_dialog`` is the same).
This module is the one place that owns that interaction contract:

* ``Enter`` confirms, ``Esc`` / ``Ctrl-C`` cancels (returns ``None``/``False``).
* Every prompt returns a ``prompt_toolkit`` ``Application`` so callers keep the
  familiar ``.run()`` shape and tests can drive it with simulated key presses.
* One style: the graphite modal theme from ``settings_modal``.

``full_screen=False`` renders the prompt inline and erases it when done, which is
what the first-run wizard needs so its console output stays on screen.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence, Tuple

from prompt_toolkit.application import Application
from prompt_toolkit.application.current import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import HSplit, Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Dialog, Label, TextArea

from aura_cli.cli.ui.settings_modal import graphite_dialog_style

Choice = Tuple[Any, str]

_MAX_VISIBLE_CHOICES = 15


def _build_app(
    *,
    title: str,
    text: str,
    body: Sequence[Any],
    focus: Any,
    key_bindings: KeyBindings,
    style: Optional[Style],
    full_screen: bool,
) -> Application[Any]:
    children: list[Any] = []
    if text:
        children.append(Label(text, dont_extend_height=True))
    children.extend(body)
    dialog = Dialog(
        title=title,
        body=HSplit(children, padding=1),
        with_background=full_screen,
    )
    return Application(
        layout=Layout(dialog, focused_element=focus),
        key_bindings=key_bindings,
        style=style or graphite_dialog_style(),
        full_screen=full_screen,
        erase_when_done=not full_screen,
        mouse_support=False,
    )


def _cancel_bindings(result: Any = None) -> KeyBindings:
    kb = KeyBindings()

    @kb.add("escape", eager=True)
    @kb.add("c-c")
    def _cancel(event: Any) -> None:
        event.app.exit(result=result)

    return kb


def _initial_index(items: Sequence[Choice], default: Any) -> int:
    for position, (value, _label) in enumerate(items):
        if value == default:
            return position
    return 0


def select_dialog(
    *,
    title: str,
    values: Sequence[Choice],
    text: str = "",
    default: Any = None,
    style: Optional[Style] = None,
    full_screen: bool = True,
) -> Application[Any]:
    """Pick one of ``values`` (``[(value, label), ...]``); ``Enter`` confirms.

    ``.run()`` returns the chosen value, or ``None`` when cancelled.
    """
    items = list(values)
    if not items:
        raise ValueError("select_dialog needs at least one choice")
    state = {"index": _initial_index(items, default)}

    def _fragments() -> StyleAndTextTuples:
        fragments: StyleAndTextTuples = []
        for position, (_value, label) in enumerate(items):
            active = position == state["index"]
            marker = "›" if active else " "
            css = "class:radio-selected" if active else "class:radio"
            fragments.append((css, f" {marker} {label}"))
            if position < len(items) - 1:
                fragments.append(("", "\n"))
        return fragments

    n_items = min(len(items), _MAX_VISIBLE_CHOICES)
    control = FormattedTextControl(
        _fragments,
        focusable=True,
        show_cursor=False,
        get_cursor_position=lambda: Point(0, state["index"]),
    )
    window = Window(
        control,
        height=n_items,
        always_hide_cursor=True,
        allow_scroll_beyond_bottom=False,
        wrap_lines=False,
    )

    kb = _cancel_bindings(None)
    last = len(items) - 1

    @kb.add("up")
    @kb.add("k")
    def _up(_event: Any) -> None:
        state["index"] = max(0, state["index"] - 1)

    @kb.add("down")
    @kb.add("j")
    def _down(_event: Any) -> None:
        state["index"] = min(last, state["index"] + 1)

    @kb.add("pageup")
    def _page_up(_event: Any) -> None:
        state["index"] = max(0, state["index"] - _MAX_VISIBLE_CHOICES)

    @kb.add("pagedown")
    def _page_down(_event: Any) -> None:
        state["index"] = min(last, state["index"] + _MAX_VISIBLE_CHOICES)

    @kb.add("home")
    def _home(_event: Any) -> None:
        state["index"] = 0

    @kb.add("end")
    def _end(_event: Any) -> None:
        state["index"] = last

    @kb.add("enter")
    def _confirm(event: Any) -> None:
        event.app.exit(result=items[state["index"]][0])

    return _build_app(
        title=title,
        text=text,
        body=[window],
        focus=window,
        key_bindings=kb,
        style=style,
        full_screen=full_screen,
    )


def input_dialog(
    *,
    title: str,
    text: str = "",
    default: str = "",
    password: bool = False,
    style: Optional[Style] = None,
    full_screen: bool = True,
) -> Application[Any]:
    """Read one line; ``Enter`` confirms (an empty line returns ``""``).

    ``.run()`` returns the text, or ``None`` when cancelled.
    """

    def _accept(buffer: Any) -> bool:
        get_app().exit(result=buffer.text)
        return True

    area = TextArea(
        text=default,
        multiline=False,
        password=password,
        wrap_lines=False,
        accept_handler=_accept,
    )
    area.buffer.cursor_position = len(default)
    return _build_app(
        title=title,
        text=text,
        body=[area],
        focus=area,
        key_bindings=_cancel_bindings(None),
        style=style,
        full_screen=full_screen,
    )


def _button_row(labels: Sequence[str], selected: int) -> StyleAndTextTuples:
    fragments: StyleAndTextTuples = []
    for position, label in enumerate(labels):
        css = "class:button.focused" if position == selected else "class:button"
        fragments.append((css, f"  {label}  "))
        fragments.append(("", "  "))
    return fragments


def confirm_dialog(
    *,
    title: str,
    text: str = "",
    default: bool = False,
    style: Optional[Style] = None,
    full_screen: bool = True,
) -> Application[Any]:
    """Yes/no question. ``y``/``n`` answer directly, ``←``/``→`` switch the highlighted
    option, ``Enter`` takes it, ``Esc`` means no. ``.run()`` returns a ``bool``.
    """
    state = {"yes": bool(default)}
    control = FormattedTextControl(
        lambda: _button_row(["Yes", "No"], 0 if state["yes"] else 1),
        focusable=True,
        show_cursor=False,
    )
    window = Window(control, height=1, always_hide_cursor=True)

    kb = _cancel_bindings(False)

    @kb.add("y")
    def _yes(event: Any) -> None:
        event.app.exit(result=True)

    @kb.add("n")
    def _no(event: Any) -> None:
        event.app.exit(result=False)

    @kb.add("left")
    @kb.add("right")
    def _toggle(_event: Any) -> None:
        state["yes"] = not state["yes"]

    @kb.add("enter")
    def _confirm(event: Any) -> None:
        event.app.exit(result=state["yes"])

    return _build_app(
        title=title,
        text=text,
        body=[window],
        focus=window,
        key_bindings=kb,
        style=style,
        full_screen=full_screen,
    )


def message_dialog(
    *,
    title: str,
    text: str = "",
    style: Optional[Style] = None,
    full_screen: bool = True,
) -> Application[Any]:
    """Informational box; ``Enter``, ``Space`` or ``Esc`` dismiss it."""
    control = FormattedTextControl(
        lambda: _button_row(["OK"], 0), focusable=True, show_cursor=False
    )
    window = Window(control, height=1, always_hide_cursor=True)

    kb = _cancel_bindings(None)

    @kb.add("enter")
    @kb.add("space")
    def _dismiss(event: Any) -> None:
        event.app.exit(result=None)

    return _build_app(
        title=title,
        text=text,
        body=[window],
        focus=window,
        key_bindings=kb,
        style=style,
        full_screen=full_screen,
    )


__all__ = [
    "Choice",
    "confirm_dialog",
    "input_dialog",
    "message_dialog",
    "select_dialog",
]
