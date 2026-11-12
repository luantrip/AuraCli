"""Key-driven contract for the single prompt layer (P1-3).

Every case feeds real key sequences through a pipe input. A watchdog turns a
prompt that is still waiting for input into a test failure instead of a frozen
suite — exactly the failure mode of stock ``radiolist_dialog`` when ``Enter``
alone does not close it.
"""

from __future__ import annotations

import signal
from typing import Any, Callable

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
import pytest

from aura_cli.cli.ui import prompts

ENTER = "\r"
ESC = "\x1b"
UP = "\x1b[A"
DOWN = "\x1b[B"
CTRL_C = "\x03"
LEFT = "\x1b[D"
RIGHT = "\x1b[C"

_SENTINEL = object()


class _StillWaiting(Exception):
    pass


def _drive(factory: Callable[[], Any], keys: str, seconds: int = 3) -> Any:
    def _alarm(*_args: Any) -> None:
        raise _StillWaiting

    previous = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(seconds)
    try:
        with create_pipe_input() as pipe:
            pipe.send_text(keys)
            with create_app_session(input=pipe, output=DummyOutput()):
                return factory().run()
    except _StillWaiting:
        pytest.fail(f"prompt still waiting for input after keys {keys!r}")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


CHOICES = [("a", "Alpha"), ("b", "Bravo"), ("c", "Charlie")]


def _select(**kwargs: Any) -> Callable[[], Any]:
    return lambda: prompts.select_dialog(title="t", values=CHOICES, **kwargs)


class TestSelect:
    def test_enter_alone_confirms_the_first_option(self) -> None:
        assert _drive(_select(), ENTER) == "a"

    def test_arrows_move_the_selection(self) -> None:
        assert _drive(_select(), DOWN + ENTER) == "b"
        assert _drive(_select(), DOWN + DOWN + ENTER) == "c"
        assert _drive(_select(), DOWN + DOWN + UP + ENTER) == "b"

    def test_selection_is_clamped_at_both_ends(self) -> None:
        assert _drive(_select(), UP + ENTER) == "a"
        assert _drive(_select(), DOWN * 9 + ENTER) == "c"

    def test_vim_keys_work(self) -> None:
        assert _drive(_select(), "jj" + ENTER) == "c"
        assert _drive(_select(), "jjk" + ENTER) == "b"

    def test_default_sets_the_initial_highlight(self) -> None:
        assert _drive(_select(default="c"), ENTER) == "c"

    def test_unknown_default_falls_back_to_first(self) -> None:
        assert _drive(_select(default="zzz"), ENTER) == "a"

    def test_escape_and_ctrl_c_cancel_with_none(self) -> None:
        assert _drive(_select(), ESC) is None
        assert _drive(_select(), CTRL_C) is None

    def test_returns_the_value_not_the_label(self) -> None:
        result = _drive(
            lambda: prompts.select_dialog(title="t", values=[(42, "forty-two")]),
            ENTER,
        )
        assert result == 42

    def test_falsy_value_is_distinguishable_from_cancel(self) -> None:
        values = [(0, "Cancelar"), (1, "Continuar")]
        picked = _drive(lambda: prompts.select_dialog(title="t", values=values), ENTER)
        cancelled = _drive(lambda: prompts.select_dialog(title="t", values=values), ESC)
        assert picked == 0 and cancelled is None

    def test_empty_choices_is_a_programming_error(self) -> None:
        with pytest.raises(ValueError):
            prompts.select_dialog(title="t", values=[])


class TestInput:
    def _input(self, **kwargs: Any) -> Callable[[], Any]:
        return lambda: prompts.input_dialog(title="t", **kwargs)

    def test_enter_confirms_typed_text(self) -> None:
        assert _drive(self._input(), "abc" + ENTER) == "abc"

    def test_empty_line_returns_empty_string_not_none(self) -> None:
        assert _drive(self._input(), ENTER) == ""

    def test_default_text_is_prefilled_and_editable(self) -> None:
        assert _drive(self._input(default="ab"), ENTER) == "ab"
        assert _drive(self._input(default="ab"), "c" + ENTER) == "abc"

    def test_password_mode_still_returns_the_real_text(self) -> None:
        assert _drive(self._input(password=True), "s3cret" + ENTER) == "s3cret"

    def test_escape_cancels_with_none(self) -> None:
        assert _drive(self._input(), "abc" + ESC) is None


class TestConfirm:
    def _confirm(self, **kwargs: Any) -> Callable[[], Any]:
        return lambda: prompts.confirm_dialog(title="t", **kwargs)

    def test_y_and_n_answer_directly(self) -> None:
        assert _drive(self._confirm(), "y") is True
        assert _drive(self._confirm(default=True), "n") is False

    def test_enter_takes_the_default(self) -> None:
        assert _drive(self._confirm(), ENTER) is False
        assert _drive(self._confirm(default=True), ENTER) is True

    def test_arrows_switch_the_highlighted_option(self) -> None:
        assert _drive(self._confirm(), RIGHT + ENTER) is True
        assert _drive(self._confirm(default=True), LEFT + ENTER) is False
        assert _drive(self._confirm(), RIGHT + LEFT + ENTER) is False

    def test_escape_means_no(self) -> None:
        assert _drive(self._confirm(default=True), ESC) is False


class TestMessage:
    def test_enter_dismisses(self) -> None:
        assert (
            _drive(lambda: prompts.message_dialog(title="t", text="x"), ENTER) is None
        )

    def test_escape_dismisses(self) -> None:
        assert _drive(lambda: prompts.message_dialog(title="t", text="x"), ESC) is None


class TestInlineMode:
    """The wizard runs inline so its console output stays on screen."""

    def test_inline_select_works(self) -> None:
        result = _drive(
            lambda: prompts.select_dialog(title="t", values=CHOICES, full_screen=False),
            DOWN + ENTER,
        )
        assert result == "b"

    def test_inline_input_works(self) -> None:
        result = _drive(
            lambda: prompts.input_dialog(title="t", full_screen=False), "k" + ENTER
        )
        assert result == "k"
