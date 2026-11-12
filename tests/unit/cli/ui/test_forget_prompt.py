"""``/tangent forget`` selector: adapter behaviour and the no-silent-forget rule."""

from __future__ import annotations

import signal
from typing import Any

from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
import pytest

from aura_cli.cli.ui.forget_prompt import select_messages_to_forget
from aura_cli.core.tangent import manager as tangent_manager

ENTER, ESC, DOWN = "\r", "\x1b", "\x1b[B"
MESSAGES = [
    {"index": 0, "preview": "primeira"},
    {"index": 2, "preview": "segunda"},
    {"index": 4, "preview": "terceira"},
]


def _drive(keys: str) -> Any:
    class _Hung(BaseException):
        pass

    def _alarm(*_a: Any) -> None:
        raise _Hung

    previous = signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(3)
    try:
        with create_pipe_input() as pipe:
            pipe.send_text(keys)
            with create_app_session(input=pipe, output=DummyOutput()):
                return select_messages_to_forget(MESSAGES)
    except _Hung:
        pytest.fail(f"still waiting after {keys!r}")
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


class TestAdapter:
    def test_first_entry_is_the_most_recent_message(self) -> None:
        assert _drive(ENTER) == 1

    def test_choosing_entry_n_forgets_the_last_n(self) -> None:
        assert _drive(DOWN + ENTER) == 2
        assert _drive(DOWN * 2 + ENTER) == 3

    def test_cancel_entry_returns_none(self) -> None:
        assert _drive(DOWN * 3 + ENTER) is None

    def test_escape_returns_none(self) -> None:
        assert _drive(ESC) is None


class TestCoreResolution:
    @pytest.fixture(autouse=True)
    def _restore(self):
        previous = tangent_manager._registered_selector
        yield
        tangent_manager.configure_forget_selector(previous)

    def test_registered_selector_is_used(self) -> None:
        tangent_manager.configure_forget_selector(lambda _m: 2)
        assert tangent_manager._forget_selection(MESSAGES) == 2

    def test_a_crashing_selector_cancels_instead_of_forgetting(self) -> None:
        """Regression: the old code returned 1 on any error and silently dropped a
        message the user never agreed to forget."""

        def boom(_m: Any) -> int:
            raise RuntimeError("terminal exploded")

        tangent_manager.configure_forget_selector(boom)
        assert tangent_manager._forget_selection(MESSAGES) is None

    def test_plain_text_fallback_parses_a_number(self, monkeypatch) -> None:
        tangent_manager.configure_forget_selector(None)
        monkeypatch.setattr("builtins.input", lambda _prompt: "2")
        assert tangent_manager._forget_selection(MESSAGES) == 2

    @pytest.mark.parametrize("raised", [ValueError, EOFError, KeyboardInterrupt])
    def test_plain_text_fallback_cancels_on_bad_input(
        self, monkeypatch, raised
    ) -> None:
        tangent_manager.configure_forget_selector(None)

        def fail(_prompt: str) -> str:
            raise raised

        monkeypatch.setattr("builtins.input", fail)
        assert tangent_manager._forget_selection(MESSAGES) is None
