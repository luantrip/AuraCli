"""Tests for cross-session telemetry persistence."""

from pathlib import Path
import tempfile

from aura_cli.application.observability.session_telemetry import SessionTelemetry


def _tmp_db() -> Path:
    import os
    fd, name = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return Path(name)


def test_record_and_get_session_cost() -> None:
    db = _tmp_db()
    try:
        tel = SessionTelemetry(db_path=db)
        tel.record_session("s1", provider="google", model="gemini-flash")
        tel.record_turn("t1", "s1", 1, input_tokens=100, output_tokens=50, cost=0.001)
        tel.finalize_session("s1", total_tokens=150, total_cost=0.001, tool_calls=1)

        result = tel.get_session_cost("s1")
        assert result is not None
        assert result["provider"] == "google"
        assert result["model"] == "gemini-flash"
        assert result["total_tokens"] == 150
        assert result["total_cost"] == 0.001
        assert result["tool_calls"] == 1
    finally:
        db.unlink(missing_ok=True)


def test_cost_summary_groups_by_provider() -> None:
    db = _tmp_db()
    try:
        tel = SessionTelemetry(db_path=db)
        tel.record_session("s1", provider="google", model="gemini-flash")
        tel.record_session("s2", provider="cerebras", model="gemma")
        tel.finalize_session("s1", total_tokens=500, total_cost=0.01)
        tel.finalize_session("s2", total_tokens=300, total_cost=0.005)

        summary = tel.get_cost_summary(days=7)
        assert summary["total_cost"] == 0.015
        assert summary["total_tokens"] == 800
        assert summary["total_sessions"] == 2
        assert len(summary["by_provider"]) == 2
    finally:
        db.unlink(missing_ok=True)


def test_chain_cost_rollup_includes_children() -> None:
    db = _tmp_db()
    try:
        tel = SessionTelemetry(db_path=db)
        tel.record_session("parent", provider="google", model="gemini")
        tel.record_session("child1", provider="google", model="gemini",
                           parent_session_id="parent")
        tel.record_session("child2", provider="cerebras", model="gemma",
                           parent_session_id="parent")
        tel.finalize_session("parent", total_tokens=200, total_cost=0.02, tool_calls=2)
        tel.finalize_session("child1", total_tokens=300, total_cost=0.03, tool_calls=1)
        tel.finalize_session("child2", total_tokens=400, total_cost=0.04, tool_calls=3)

        chain = tel.get_chain_cost("parent")
        assert chain["parent_session"] == "parent"
        assert chain["child_count"] == 2
        assert chain["total_tokens"] == 900
        assert chain["total_cost"] == 0.09
        assert chain["total_tool_calls"] == 6
    finally:
        db.unlink(missing_ok=True)


def test_disabled_telemetry_is_noop() -> None:
    db = _tmp_db()
    try:
        tel = SessionTelemetry(db_path=db, enabled=False)
        tel.record_session("s1")
        tel.finalize_session("s1", total_tokens=100)
        tel.record_turn("t1", "s1", 1)

        assert tel.get_session_cost("s1") is None
    finally:
        db.unlink(missing_ok=True)


def test_prune_old_sessions_deletes_expired() -> None:
    db = _tmp_db()
    try:
        tel = SessionTelemetry(db_path=db, retention_days=-1)
        tel.record_session("old1", provider="google", model="gemini")
        tel.finalize_session("old1", total_tokens=100, total_cost=0.01)

        deleted = tel.prune_old_sessions()
        assert deleted >= 1

        assert tel.get_session_cost("old1") is None
    finally:
        db.unlink(missing_ok=True)


def test_thread_safety_does_not_deadlock() -> None:
    import threading

    db = _tmp_db()
    try:
        tel = SessionTelemetry(db_path=db)

        def writer(session_id: str) -> None:
            tel.record_session(session_id, provider="test", model="test")
            tel.finalize_session(session_id, total_tokens=10, total_cost=0.001)

        threads = [threading.Thread(target=writer, args=(f"s{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(5):
            result = tel.get_session_cost(f"s{i}")
            assert result is not None
            assert result["total_tokens"] == 10
    finally:
        db.unlink(missing_ok=True)


def test_record_turn_persists_tool_info() -> None:
    db = _tmp_db()
    try:
        tel = SessionTelemetry(db_path=db)
        tel.record_session("s1", provider="google", model="gemini")
        tel.record_turn(
            "t1", "s1", 1,
            input_tokens=50,
            output_tokens=30,
            cost=0.002,
            tool_name="read_file",
            duration_ms=150,
        )

        import sqlite3
        conn = sqlite3.connect(str(db))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM turns WHERE id = 't1'").fetchone()
        conn.close()

        assert row is not None
        assert row["tool_name"] == "read_file"
        assert row["duration_ms"] == 150
        assert row["input_tokens"] == 50
    finally:
        db.unlink(missing_ok=True)
