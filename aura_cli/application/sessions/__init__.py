"""Session-oriented application use cases."""

from .chat_mapping import chat_messages_to_history, role_to_sender
from .context_snapshot import (
    SnapshotPlan,
    build_snapshot_history,
    plan_snapshot,
    truncate_history,
)
from .history import (
    SessionEntry,
    query_session_history,
    session_entry_from_jsonl,
    session_entry_from_snapshot,
)
from .turn_repository import SCHEMA_VERSION, RestoredSession, TurnRepository
from .use_cases import (
    LoadSessionOutcome,
    LoadSessionStatus,
    SaveSessionOutcome,
    count_conversation_messages,
    load_session_into_workspace,
    save_workspace_session,
)

__all__ = [
    "SCHEMA_VERSION",
    "LoadSessionOutcome",
    "LoadSessionStatus",
    "RestoredSession",
    "SaveSessionOutcome",
    "SessionEntry",
    "SnapshotPlan",
    "TurnRepository",
    "build_snapshot_history",
    "chat_messages_to_history",
    "count_conversation_messages",
    "load_session_into_workspace",
    "plan_snapshot",
    "query_session_history",
    "role_to_sender",
    "save_workspace_session",
    "session_entry_from_jsonl",
    "session_entry_from_snapshot",
    "truncate_history",
]
