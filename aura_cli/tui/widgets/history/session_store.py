"""Filesystem adapter for application session-history models."""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path

from aura_cli.application.sessions.history import (
    SessionEntry,
    session_entry_from_jsonl,
    session_entry_from_snapshot,
)
from aura_cli.core.logger import get_logger
from aura_cli.core.sessions.external_discovery import discover_external_sessions
from aura_cli.core.sessions.external_import import inspect_external_session

logger = get_logger(__name__)


def parse_session_json(path: Path) -> SessionEntry | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return session_entry_from_snapshot(
            data,
            path=path,
            fallback_timestamp=datetime.fromtimestamp(path.stat().st_mtime),
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        logger.warning("Error parsing JSON session %s: %s", path, error)
        return None


def parse_session_file(path: Path) -> SessionEntry | None:
    try:
        return session_entry_from_jsonl(
            path.read_text(encoding="utf-8").splitlines(),
            path=path,
            timestamp=datetime.fromtimestamp(path.stat().st_mtime),
        )
    except (OSError, TypeError, ValueError) as error:
        logger.warning("Error parsing session %s: %s", path, error)
        return None


def load_sessions(
    sessions_dir: Path, *, include_external: bool = False
) -> list[SessionEntry]:
    if not sessions_dir.exists():
        logger.info("Sessions directory does not exist: %s", sessions_dir)
    sessions: list[SessionEntry] = []
    if sessions_dir.exists():
        seen: set[str] = set()
        for path in sessions_dir.glob("*.json"):
            if entry := parse_session_json(path):
                sessions.append(entry)
                seen.add(entry.session_id)
        for path in sessions_dir.glob("*.jsonl"):
            if path.stem not in seen and (entry := parse_session_file(path)):
                sessions.append(entry)
    if include_external:
        sessions.extend(_load_external_sessions())
    return sorted(sessions, key=lambda entry: entry.timestamp, reverse=True)


def _load_external_sessions() -> list[SessionEntry]:
    entries: list[SessionEntry] = []
    for candidate in (
        *discover_external_sessions("grok"),
        *discover_external_sessions("codex"),
    ):
        try:
            data = inspect_external_session(str(candidate.path))
            timestamp = datetime.fromtimestamp(candidate.path.stat().st_mtime)
        except (OSError, ValueError):
            continue
        messages = list(data.messages)
        user_messages = [
            str(item.get("content", ""))[:200]
            for item in messages
            if item.get("role") == "user" and item.get("content")
        ]
        entries.append(
            SessionEntry(
                session_id=f"{candidate.provider}:{candidate.session_id}",
                path=candidate.path,
                timestamp=timestamp,
                cwd=data.cwd or candidate.cwd,
                first_message=user_messages[0] if user_messages else None,
                last_message=user_messages[-1] if user_messages else None,
                message_count=len(messages),
                search_blob="\n".join(
                    str(item.get("content", "")) for item in messages
                ).casefold(),
                source_format=data.source_format,
                external=True,
            )
        )
    return entries


__all__ = ["SessionEntry", "load_sessions", "parse_session_file", "parse_session_json"]
