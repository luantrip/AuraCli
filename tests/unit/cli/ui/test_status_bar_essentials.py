"""P1-7 — the footer shows what you need, and never a made-up number.

Rendered through the real ``StatusBar`` and a real ``StatsTracker`` so the
assertions describe what a user would read above the prompt.
"""

from __future__ import annotations

import io

from rich.console import Console

from aura_cli.application.workspace.context_usage import (
    DEFAULT_CONTEXT_WINDOW,
    context_window_for_model,
)
from aura_cli.cli.ui.components.layout.status_bar import StatusBar
from aura_cli.core.stats import StatsTracker

GEMINI = "gemini/gemini-2.5-flash"
GPT = "gpt-4o"


def _bar(
    *,
    model: str = GEMINI,
    status: str = "idle",
    context_tokens: int = 0,
    spent_tokens: int = 0,
    cost: float = 0.0,
    skip: bool = False,
    branch: str | None = None,
    turn: float = 0.0,
    verbose: bool = False,
    width: int = 100,
) -> str:
    stats = StatsTracker()
    stats.set_model(model)
    stats.set_status(status, "")
    stats.skip_confirmations = skip
    stats.context_tokens = context_tokens
    if spent_tokens:
        stats.add_tokens(
            {
                "total_tokens": spent_tokens,
                "prompt_tokens": spent_tokens,
                "completion_tokens": 0,
            },
            model=model,
        )
    if cost:
        stats.total_cost = cost
    bar = StatusBar(stats, verbose=verbose)
    bar._get_git_branch = lambda: branch  # type: ignore[method-assign]
    if turn:
        bar.record_turn_metrics(exec_time=turn, model=model)
    buffer = io.StringIO()
    Console(file=buffer, width=width, color_system=None).print(
        bar.render(console_width=width)
    )
    return buffer.getvalue()


# --------------------------------------------------------------- context % -----
def test_context_percentage_uses_the_live_history_not_cumulative_spend() -> None:
    """Regression: 96k tokens *billed* over a session (each call re-sends the whole
    history) used to read as 75% of a fixed 128k window while the real history was
    24k -- 19% of a gpt-4o window."""
    out = _bar(model=GPT, context_tokens=24_000, spent_tokens=96_000)
    assert "Contexto 19%" in out
    assert "75%" not in out
    assert "96.0k tok" in out  # the spend is still reported, honestly labelled


def test_context_window_follows_the_model() -> None:
    same_history = 100_000
    assert "Contexto 10%" in _bar(model=GEMINI, context_tokens=same_history)
    assert "Contexto 78%" in _bar(model=GPT, context_tokens=same_history)


def test_no_measurement_means_no_percentage_instead_of_an_invented_one() -> None:
    out = _bar(context_tokens=0, spent_tokens=50_000)
    assert "Contexto" not in out
    assert "50.0k tok" in out


def test_unknown_model_uses_the_conservative_window() -> None:
    assert context_window_for_model("totally/unknown") == DEFAULT_CONTEXT_WINDOW
    assert context_window_for_model(None) == DEFAULT_CONTEXT_WINDOW
    assert context_window_for_model("") == DEFAULT_CONTEXT_WINDOW
    assert "Contexto 50%" in _bar(
        model="totally/unknown", context_tokens=DEFAULT_CONTEXT_WINDOW // 2
    )


def test_context_percentage_follows_the_model_of_the_last_turn() -> None:
    stats = StatsTracker()
    stats.set_model(GEMINI)
    stats.context_tokens = 64_000
    bar = StatusBar(stats, verbose=False)
    bar.record_turn_metrics(exec_time=1.0, model=GPT)  # fallback switched models
    buffer = io.StringIO()
    Console(file=buffer, width=100, color_system=None).print(
        bar.render(console_width=100)
    )
    assert "Contexto 50%" in buffer.getvalue()  # 64k of gpt-4o's 128k


# ------------------------------------------------------- essentials vs detail ---
def test_default_mode_shows_only_the_essentials() -> None:
    out = _bar(
        context_tokens=1_000,
        spent_tokens=2_000,
        cost=0.25,
        branch="main",
        turn=3.2,
        skip=True,
    )
    for detail in ("$0.25", "last", "git:main", "(no confirm)"):
        assert detail not in out, detail
    for essential in ("Ocioso", "gemini-2.5-flash", "Contexto", "tok"):
        assert essential in out, essential


def test_verbose_mode_adds_cost_last_turn_and_branch() -> None:
    out = _bar(
        context_tokens=1_000,
        spent_tokens=2_000,
        cost=0.25,
        branch="main",
        turn=3.2,
        verbose=True,
    )
    for detail in ("$0.2500", "last 3.2s", "git:main"):
        assert detail in out, detail


def test_auto_run_is_not_repeated_in_the_footer_in_either_mode() -> None:
    """The prompt already says ``(sem confirmação)`` where the action happens."""
    assert "sem confirmação" not in _bar(skip=True, verbose=False)
    assert "sem confirmação" not in _bar(skip=True, verbose=True)


def test_verbose_follows_the_setting_when_not_forced(monkeypatch) -> None:
    from aura_cli.cli.ui.components import status_bar as module

    stats = StatsTracker()
    stats.set_model(GEMINI)
    stats.context_tokens = 1_000
    bar = StatusBar(stats)
    bar.record_turn_metrics(exec_time=2.0, model=GEMINI)

    def rendered() -> str:
        buffer = io.StringIO()
        Console(file=buffer, width=100, color_system=None).print(
            bar.render(console_width=100)
        )
        return buffer.getvalue()

    monkeypatch.setattr(module.config_manager, "get", lambda key, *a: False)
    assert "último" not in rendered()
    monkeypatch.setattr(module.config_manager, "get", lambda key, *a: True)
    assert "last 2.0s" in rendered()  # applies on the next render, no restart


# --------------------------------------------------------------------- states ---
def test_every_state_the_system_writes_has_a_label() -> None:
    """``StatusManager.set_working`` writes ``working``; the bar used to read it as
    idle (``Ocioso``) while the spinner was visibly spinning."""
    assert "Processing" in _bar(status="working")
    assert "Processing" in _bar(status="running")
    assert "Raciocinando" in _bar(status="thinking")
    assert "Executando" in _bar(status="executing")
    assert "Ocioso" in _bar(status="idle")


# ---------------------------------------------------------------------- width ---
def test_default_footer_fits_one_line_at_80_columns_with_a_long_branch() -> None:
    out = _bar(
        context_tokens=24_000,
        spent_tokens=96_000,
        branch="feature/refatoracao-ui-imersiva",
        verbose=False,
        width=80,
    )
    assert len([line for line in out.splitlines() if line.strip()]) == 1


def test_footer_stacks_in_a_narrow_terminal() -> None:
    out = _bar(context_tokens=24_000, spent_tokens=96_000, width=50)
    assert len([line for line in out.splitlines() if line.strip()]) == 2


def test_the_fallback_window_stays_conservative() -> None:
    """An unknown model is assumed small: wrongly assuming a huge window would delay
    compaction until the provider rejects the request."""
    assert DEFAULT_CONTEXT_WINDOW == 32_000


def test_the_window_table_is_the_single_source_for_compaction() -> None:
    """History compaction and the footer must agree on a model's window."""
    from aura_cli.core.context.base import compression_threshold_for_model

    for model in (
        GEMINI,
        GPT,
        "claude-sonnet-4-6",
        "cerebras/gpt-oss-120b",
        "x/unknown",
    ):
        window = context_window_for_model(model)
        assert compression_threshold_for_model(model) == max(8_000, window // 10 * 4)


# --------------------------------------------- measured once per prompt (loop) ---
class _Loop:
    """Minimal host for ``SessionLifecycleMixin`` -- just what the method touches."""

    def __init__(self, history: list[dict[str, str]]) -> None:
        from aura_cli.cli.session_lifecycle import SessionLifecycleMixin

        self.conversation_history = history
        self.stats = StatsTracker()
        self.logger = __import__("logging").getLogger("test")
        self._measure = SessionLifecycleMixin._refresh_context_measure.__get__(self)

    def refresh(self) -> None:
        self._measure()


def test_footer_measure_tracks_growth_and_compaction_between_prompts() -> None:
    """Regression: ``context_tokens`` was only written before an LLM call, so the
    footer showed the previous turn's size after a reply or a compaction."""
    history = [{"role": "user", "content": "x" * 4_000}]
    loop = _Loop(history)

    loop.refresh()
    first = loop.stats.context_tokens
    assert first > 0

    history.append({"role": "assistant", "content": "y" * 40_000})  # reply arrives
    loop.refresh()
    assert loop.stats.context_tokens > first

    history[:] = [{"role": "system", "content": "resumo"}]  # compaction / restore
    loop.refresh()
    assert loop.stats.context_tokens < first


def test_a_failing_measure_never_blocks_the_prompt() -> None:
    loop = _Loop([{"role": "user", "content": None}])  # type: ignore[dict-item]
    loop.stats = None  # type: ignore[assignment]
    loop.refresh()  # must not raise


def test_main_loop_measures_the_history_right_before_drawing_the_footer() -> None:
    """Pins the *call site*: measure -> footer -> prompt, in that order."""
    from unittest.mock import MagicMock

    from aura_cli.cli.session_lifecycle import SessionLifecycleMixin

    order: list[str] = []

    class Host(SessionLifecycleMixin):
        def __init__(self) -> None:
            self.shutdown_event = None
            self.logger = MagicMock()
            self.stats = MagicMock()
            self.conversation_history = [{"role": "user", "content": "oi"}]
            self.tangent_manager = MagicMock(get_indicator=lambda: "")
            self._todo_done_count = 0
            self.ui = MagicMock()
            self.ui.status_queue = MagicMock()
            self.ui.display_status_bar.side_effect = lambda *a, **k: order.append(
                "footer"
            )
            self.ui.prompt.side_effect = lambda *a, **k: (
                order.append("prompt"),
                "/exit",
            )[1]

        def _refresh_context_measure(self) -> None:
            order.append("measure")

        def _handle_exit_command(self, command: str) -> bool:
            return True  # leave the loop after the first prompt

        def _handle_auto_run_command(self, command: str) -> bool:
            return False

        def shutdown(self, timeout: float = 10.0) -> bool:
            return True

    from unittest.mock import patch

    with (
        patch("aura_cli.cli.session_lifecycle.handle_status_updates"),
        patch("aura_cli.cli.session_lifecycle.refresh_todo_tracker"),
        patch(
            "aura_cli.cli.session_lifecycle.check_and_notify_task_completion",
            return_value=0,
        ),
        patch("aura_cli.cli.session_lifecycle.register_ui"),
        patch("aura_cli.cli.session_lifecycle.unregister_ui"),
    ):
        Host().run()

    assert order == ["measure", "footer", "prompt"], order
