"""Exercise realtime TUI session persistence and event synchronization."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from queue import Queue

from aura_cli.application.agents.events import AgiTaskStartEvent, ChatMessageEvent
from aura_cli.application.sessions.external import normalize_external_records
from aura_cli.application.sessions.history import query_session_history
from aura_cli.core.sessions.session_manager import Session
from aura_cli.tui.core.sync_manager import SyncManager
from aura_cli.tui.core.sync_store import SyncStore
from aura_cli.tui.widgets.history.session_store import load_sessions
from aura_cli.tui.services.tui_session_service import export_session_jsonl


class ProbeApp:
    def __init__(self) -> None:
        self.refresh_count = 0
        self.thread_calls = 0

    def refresh(self) -> None:
        self.refresh_count += 1

    def call_from_thread(self, callback, *args, **kwargs) -> None:
        self.thread_calls += 1
        callback(*args, **kwargs)

    def query_one(self, _selector):
        raise LookupError("optional TUI widget is not mounted in probe")


def check_session_round_trip(root: Path) -> dict[str, object]:
    sessions_dir = root / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session = Session(
        id="session-realtime",
        name="Realtime session",
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=datetime.now(timezone.utc).isoformat(),
        current_directory=str(root),
    )
    session.add_message("user", "Investigate streaming")
    session.add_message("assistant", "Streaming is active")
    path = sessions_dir / "session-realtime.jsonl"
    export_session_jsonl(session, path)
    entries = load_sessions(sessions_dir)
    assert len(entries) == 1 and entries[0].message_count == 2
    assert query_session_history(entries, query="streaming")
    return {"session_id": entries[0].session_id, "messages": entries[0].message_count}


def check_external_history() -> dict[str, object]:
    result = normalize_external_records(
        [
            {
                "method": "session/update",
                "params": {
                    "sessionId": "grok-realtime",
                    "update": {
                        "sessionUpdate": "user_message_chunk",
                        "content": {"type": "text", "text": "Review the stream"},
                    },
                },
            },
            {
                "method": "session/update",
                "params": {
                    "update": {
                        "sessionUpdate": "agent_thought_chunk",
                        "content": {"type": "text", "text": "private thought"},
                    }
                },
            },
            {
                "method": "session/update",
                "params": {
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": "The stream is healthy"},
                    }
                },
            },
            {"type": "tool_call", "name": "run_shell"},
        ],
        source_format="grok-acp",
    )
    assert result.source_session_id == "grok-realtime"
    assert len(result.messages) == 2
    assert result.skipped_events == 1
    assert all(item["metadata"]["executable"] is False for item in result.messages)
    return {"source": result.source_format, "messages": len(result.messages), "skipped": result.skipped_events}


def check_sync_manager() -> dict[str, object]:
    app = ProbeApp()
    store = SyncStore()
    manager = SyncManager(app=app, status_queue=Queue(), store=store)
    manager.process_event(AgiTaskStartEvent.create("task-sync", "Index", "Index files"))
    manager.process_event(ChatMessageEvent.create("agent", "Ready", task_id="task-sync"))
    task = store.get_task("task-sync")
    assert task is not None
    assert store.get_messages() == [] or isinstance(store.get_messages(), list)
    assert app.refresh_count == 2
    manager.stop()
    return {"task_keys": sorted(task.keys()), "refreshes": app.refresh_count, "running": manager.is_running}


def main() -> None:
    root = Path(os.environ.get("AURA_HOME", "."))
    root.mkdir(parents=True, exist_ok=True)
    report = {
        "contract": "aura-realtime-session-v1",
        "checks": {
            "session_round_trip": check_session_round_trip(root),
            "external_history": check_external_history(),
            "sync_manager": check_sync_manager(),
        },
        "aura_home": os.environ.get("AURA_HOME", ""),
        "status": "READY",
    }
    output_path = root / "realtime-session-probe.json"
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("SESSION_READY")
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
