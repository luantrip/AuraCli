"""Session-history models, parsing and queries without filesystem I/O."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class SessionEntry:
    session_id: str
    path: Path
    timestamp: datetime
    cwd: str | None
    first_message: str | None
    last_message: str | None
    message_count: int
    search_blob: str
    source_format: str | None = None
    external: bool = False

    def relative_time(self, now: datetime | None = None) -> str:
        current = now or datetime.now(self.timestamp.tzinfo)
        seconds = max(0, int((current - self.timestamp).total_seconds()))
        if seconds < 60:
            return f"{seconds}s atrá"
        minutes = seconds // 60
        if minutes < 60:
            return f"{minutes}m atrá"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h atrá"
        days = hours // 24
        if days < 30:
            return f"{days}d atrá"
        if days < 365:
            return f"{days // 30}mo atrá"
        return f"{days // 365}a atrá"

    @property
    def short_cwd(self) -> str:
        if not self.cwd:
            return "—"
        parts = Path(self.cwd).parts
        return self.cwd if len(parts) <= 2 else ".../" + "/".join(parts[-2:])


def session_entry_from_snapshot(
    data: Mapping[str, Any], *, path: Path, fallback_timestamp: datetime
) -> SessionEntry:
    history = data.get("conversation_history", [])
    timestamp = _parse_timestamp(
        data.get("updated_at") or data.get("created_at"), fallback_timestamp
    )
    return _build_entry(
        history,
        session_id=str(data.get("id", path.stem)),
        path=path,
        timestamp=timestamp,
        cwd=data.get("current_directory"),
    )


def session_entry_from_jsonl(
    lines: Iterable[str], *, path: Path, timestamp: datetime
) -> SessionEntry:
    entries = []
    cwd = None
    for line in lines:
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        entries.append(value)
        cwd = value.get("cwd") or value.get("metadata", {}).get("cwd") or cwd
    return _build_entry(
        entries, session_id=path.stem, path=path, timestamp=timestamp, cwd=cwd
    )


def query_session_history(
    entries: Sequence[SessionEntry],
    *,
    query: str = "",
    cwd: str | None = None,
) -> list[SessionEntry]:
    tokens = query.casefold().split()
    return [
        entry
        for entry in entries
        if (cwd is None or entry.cwd == cwd)
        and all(token in entry.search_blob for token in tokens)
    ]


def _build_entry(
    history: Iterable[Mapping[str, Any]],
    *,
    session_id: str,
    path: Path,
    timestamp: datetime,
    cwd: str | None,
) -> SessionEntry:
    items = list(history)
    user_messages = [
        str(item.get("content", ""))[:200]
        for item in items
        if item.get("role") == "user" and item.get("content")
    ]
    return SessionEntry(
        session_id=session_id,
        path=path,
        timestamp=timestamp,
        cwd=cwd,
        first_message=user_messages[0] if user_messages else None,
        last_message=user_messages[-1] if user_messages else None,
        message_count=len(items),
        search_blob="\n".join(
            str(item.get("content", "")) for item in items
        ).casefold(),
    )


def _parse_timestamp(value: Any, fallback: datetime) -> datetime:
    if not value:
        return fallback
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return fallback


__all__ = [
    "SessionEntry",
    "query_session_history",
    "session_entry_from_jsonl",
    "session_entry_from_snapshot",
]
