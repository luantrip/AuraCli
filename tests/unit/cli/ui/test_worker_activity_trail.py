"""Structured worker events become a one-line CLI activity trail.

Driven through the real ``WorkerActivityRenderer`` + ``RenderCoordinator`` and a
recording console, so the assertions describe what a user sees during ``/agi``.
"""

from __future__ import annotations

import io

from rich.console import Console

from aura_cli.application.agents.events import (
    AgiEventType,
    create_task_complete,
    create_task_start,
    create_task_update,
)
from aura_cli.cli.ui.composition.worker_activity import WorkerActivityRenderer
from aura_cli.cli.ui.rendering import RenderCoordinator
from aura_cli.core.events.agi_events import (
    ChatMessageEvent,
    ToolExecutingEvent,
    ToolResultEvent,
)
from aura_cli.core.stats import StatsTracker


def _harness() -> tuple[WorkerActivityRenderer, io.StringIO]:
    buffer = io.StringIO()
    console = Console(file=buffer, width=92, color_system=None, force_terminal=False)
    render = RenderCoordinator(console, StatsTracker())
    return WorkerActivityRenderer(render), buffer


_counter = {"n": 0}


def _tool_start(task: str, name: str, **args) -> dict:
    _counter["n"] += 1
    return ToolExecutingEvent.create(
        task_id=task, tool_name=name, tool_args=args, execution_id=f"x{_counter['n']}"
    ).to_dict()


def _tool_end(
    task: str, name: str, exec_id: str, *, success: bool, result="ok"
) -> dict:
    return ToolResultEvent.create(
        task_id=task,
        tool_name=name,
        result=result,
        success=success,
        execution_id=exec_id,
    ).to_dict()


def _lines(buffer: io.StringIO) -> list[str]:
    return [line.strip() for line in buffer.getvalue().splitlines() if line.strip()]


class TestTrail:
    def test_tool_start_and_result_each_produce_one_line(self) -> None:
        wr, buf = _harness()
        start = _tool_start("t1", "write_file", path="src/app.py")
        assert wr.render_event(start) is True
        assert (
            wr.render_event(
                _tool_end(
                    "t1", "write_file", start["data"]["execution_id"], success=True
                )
            )
            is True
        )
        lines = _lines(buf)
        assert len(lines) == 2
        assert "running" in lines[0] and "src/app.py" in lines[0]
        assert "completed" in lines[1]

    def test_task_complete_uses_the_task_title_not_the_raw_event_name(self) -> None:
        wr, buf = _harness()
        wr.render_event(create_task_start("t1", "Criar API", "obj"))
        wr.render_event(create_task_complete("t1", True, "API pronta"))
        out = buf.getvalue()
        assert "Criar API · completed" in out
        assert "agi task complete" not in out

    def test_a_failed_tool_is_a_red_line_not_an_error_panel(self) -> None:
        wr, buf = _harness()
        start = _tool_start("t1", "run_command", command="pytest -q")
        wr.render_event(start)
        wr.render_event(
            _tool_end(
                "t1",
                "run_command",
                start["data"]["execution_id"],
                success=False,
                result="2 failed",
            )
        )
        lines = _lines(buf)
        # A panel would add box-drawing characters and several lines; a trail line
        # is a single row with the error glyph.
        assert not any(ch in buf.getvalue() for ch in "╭╰│")
        assert any("falhou" in line for line in lines)

    def test_markup_like_paths_are_shown_literally_and_never_dropped(self) -> None:
        wr, buf = _harness()
        for path in ("app/[id]/page.tsx", "notes/[/bold]x.md", "docs/[red]x.md"):
            before = len(buf.getvalue())
            assert wr.render_event(_tool_start("t1", "write_file", path=path)) is True
            assert path in buf.getvalue()[before:], path

    def test_updates_carry_their_own_message(self) -> None:
        wr, buf = _harness()
        wr.render_event(create_task_start("t1", "Tarefa", "obj"))
        wr.render_event(create_task_update("t1", "running", "Planejando a estrutura"))
        assert "Planejando a estrutura" in buf.getvalue()


class TestConsumedButNotRendered:
    def test_chat_messages_are_not_consumed_here(self) -> None:
        wr, buf = _harness()
        chat = ChatMessageEvent.create(
            sender="assistant", content="Resposta final", task_id="t1"
        ).to_dict()
        assert wr.render_event(chat) is False
        assert buf.getvalue() == ""  # left for the chat feed

    def test_chat_is_excluded_both_by_the_type_set_and_the_explicit_guard(self) -> None:
        """Two independent barriers keep chat off the activity trail; if either is
        removed the other must still hold, and this pins both."""
        from aura_cli.cli.ui.composition import worker_activity as module

        chat_type = AgiEventType.CHAT_MESSAGE.value
        # 1) chat is not in the structured set
        assert chat_type not in module._STRUCTURED_EVENT_TYPES
        # 2) even if it were, the explicit guard returns early (simulate the leak)
        wr, buf = _harness()
        leaked = module._STRUCTURED_EVENT_TYPES | {chat_type}
        original = module._STRUCTURED_EVENT_TYPES
        module._STRUCTURED_EVENT_TYPES = leaked  # type: ignore[assignment]
        try:
            chat = ChatMessageEvent.create(
                sender="assistant", content="X", task_id="t1"
            ).to_dict()
            assert wr.render_event(chat) is False
            assert buf.getvalue() == ""
        finally:
            module._STRUCTURED_EVENT_TYPES = original  # type: ignore[assignment]

    def test_non_dict_and_plain_text_fall_through(self) -> None:
        wr, _ = _harness()
        assert wr.render_event("[Aura AGI] texto legado") is False
        assert wr.render_event(None) is False
        assert wr.render_event({"type": "totally_unknown"}) is False

    def test_a_malformed_structured_event_does_not_crash(self) -> None:
        wr, _ = _harness()
        # Recognized type but missing required fields -> not consumed, no raise.
        assert wr.render_event({"type": AgiEventType.TOOL_EXECUTING.value}) is False


class TestStatefulAcrossEvents:
    def test_one_reducer_per_renderer_keeps_elapsed_and_identity(self) -> None:
        """The renderer holds a single reducer, so a tool's start/result correlate
        and parallel calls of the same tool each get a line."""
        wr, buf = _harness()
        a = _tool_start("t1", "read_file", path="a.py")
        b = _tool_start("t1", "read_file", path="b.py")
        wr.render_event(a)
        wr.render_event(b)
        out = buf.getvalue()
        assert "a.py" in out and "b.py" in out


class TestIntegrationThroughHandleStatusUpdates:
    """The real CLI entry point: ``handle_status_updates`` drains the queue."""

    def _ui(self):
        from aura_cli.cli.ui.manager import UIManager

        buffer = io.StringIO()
        ui = UIManager(console=Console(file=buffer, width=92, color_system=None))
        return ui, buffer

    def _drain(self, ui, events) -> None:
        import queue

        from aura_cli.cli.helpers import handle_status_updates

        q: queue.Queue = queue.Queue()
        for ev in events:
            q.put(ev)
        handle_status_updates(q, ui=ui)

    def test_full_agi_cycle_shows_tools_and_terminal_state(self) -> None:
        ui, buf = self._ui()
        start = _tool_start("t1", "write_file", path="src/app.py")
        self._drain(
            ui,
            [
                create_task_start("t1", "Criar API", "obj"),
                start,
                _tool_end(
                    "t1", "write_file", start["data"]["execution_id"], success=True
                ),
                create_task_complete("t1", True, "pronto"),
            ],
        )
        out = buf.getvalue()
        assert "src/app.py" in out  # the tool is now visible (regression target)
        assert "Criar API · completed" in out
        assert "agi task complete" not in out

    def test_chat_message_still_reaches_the_worker_feed(self) -> None:
        ui, buf = self._ui()
        self._drain(
            ui,
            [
                {
                    "type": "chat_message",
                    "task_id": "t1",
                    "data": {"role": "assistant", "content": "[Aura AGI] Analisando"},
                }
            ],
        )
        assert "Analisando" in buf.getvalue()


class _FakeClock:
    """Deterministic replacement for ``datetime`` inside work_item_projection."""

    def __init__(self) -> None:
        from datetime import datetime, timezone

        self.base = datetime.now(timezone.utc)
        self.offset = 0.0

    def advance(self, seconds: float) -> None:
        self.offset = seconds

    def cls(self):
        from datetime import datetime, timedelta

        clock = self

        class _Dt(datetime):
            @classmethod
            def now(cls, tz=None):
                return clock.base + timedelta(seconds=clock.offset)

        return _Dt


class TestHeartbeatForSilentTools:
    """A tool that runs silently still shows signs of life in the activity trail.

    The CLI loop blocks in the prompt, so a long tool emits no events. The
    heartbeat is driven from ``handle_status_updates`` on every refresh, *before*
    the empty-queue early return.
    """

    def _setup(self, monkeypatch):
        import aura_cli.application.presentation.work_item_projection as projection

        clock = _FakeClock()
        monkeypatch.setattr(projection, "datetime", clock.cls())
        wr, buf = _harness()
        start = _tool_start("t1", "run_command", command="pytest -q")
        wr.render_event(start)
        buf.truncate(0)
        buf.seek(0)
        return wr, buf, clock, start

    def test_no_line_before_the_first_interval(self, monkeypatch) -> None:
        wr, buf, clock, _ = self._setup(monkeypatch)
        clock.advance(5)
        assert wr.heartbeat() == 0
        assert buf.getvalue() == ""

    def test_elapsed_line_appears_after_the_interval_and_is_deduplicated(
        self, monkeypatch
    ) -> None:
        wr, buf, clock, _ = self._setup(monkeypatch)
        # started_at comes from the event's real timestamp, so elapsed is the offset
        # minus a few ms; assert the bucket, not the exact second.
        clock.advance(20.5)
        assert wr.heartbeat() == 1
        assert "20s" in buf.getvalue()
        before = buf.getvalue()
        clock.advance(22.5)  # same 15s bucket -> nothing new
        assert wr.heartbeat() == 0
        assert buf.getvalue() == before
        clock.advance(40.5)  # next bucket
        assert wr.heartbeat() == 1
        assert "40s" in buf.getvalue()

    def test_heartbeat_stops_once_the_tool_finishes(self, monkeypatch) -> None:
        wr, buf, clock, start = self._setup(monkeypatch)
        wr.render_event(
            _tool_end("t1", "run_command", start["data"]["execution_id"], success=True)
        )
        buf.truncate(0)
        buf.seek(0)
        clock.advance(120)
        assert wr.heartbeat() == 0
        assert buf.getvalue() == ""

    def test_markup_in_a_heartbeat_line_is_literal(self, monkeypatch) -> None:
        import aura_cli.application.presentation.work_item_projection as projection

        clock = _FakeClock()
        monkeypatch.setattr(projection, "datetime", clock.cls())
        wr, buf = _harness()
        wr.render_event(_tool_start("t1", "write_file", path="app/[id]/page.tsx"))
        buf.truncate(0)
        buf.seek(0)
        clock.advance(20)
        wr.heartbeat()
        assert "app/[id]/page.tsx" in buf.getvalue()


class TestHeartbeatWiring:
    def _ui(self):
        from aura_cli.cli.ui.manager import UIManager

        buffer = io.StringIO()
        return UIManager(
            console=Console(file=buffer, width=92, color_system=None)
        ), buffer

    def test_heartbeat_runs_even_when_the_queue_is_empty(self, monkeypatch) -> None:
        """The silent-tool case: no events queued, yet the tick must still fire."""
        import queue

        from aura_cli.cli.helpers import handle_status_updates

        ui, _ = self._ui()
        calls: list[int] = []
        monkeypatch.setattr(ui.worker_activity, "heartbeat", lambda: calls.append(1))
        handle_status_updates(queue.Queue(), ui=ui)
        assert calls == [1]

    def test_a_failing_heartbeat_never_breaks_the_refresh(self, monkeypatch) -> None:
        import queue

        from aura_cli.cli.helpers import handle_status_updates

        ui, _ = self._ui()

        def _boom() -> int:
            raise RuntimeError("clock exploded")

        monkeypatch.setattr(ui.worker_activity, "heartbeat", _boom)
        q: queue.Queue = queue.Queue()
        q.put(create_task_start("t1", "Tarefa", "obj"))
        handle_status_updates(q, ui=ui)  # must not raise
