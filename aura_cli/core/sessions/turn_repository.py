"""Atomic JSON adapter for the canonical turn repository."""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
from typing import Any, Sequence

from aura_cli.application.execution import TurnExecution
from aura_cli.application.sessions.turn_repository import (
    SCHEMA_VERSION,
    RestoredSession,
)

_SECRET_TEXT = re.compile(
    r"(?i)(?:(api[_-]?key|token|password|authorization)\s*[:=]\s*)((?:Bearer\s+)?[^\s,;]+)|"
    r"\bBearer\s+[A-Za-z0-9._~+/=-]+|\bsk-[A-Za-z0-9_-]{8,}"
)


class AtomicTurnRepository:
    """Persist the conversation and all operational facts in one atomic snapshot."""

    def __init__(self, storage_path: Path) -> None:
        self.storage_path = storage_path

    def persist_turn(
        self,
        turn: TurnExecution,
        conversation_history: Sequence[dict[str, Any]],
        *,
        current_directory: str,
    ) -> None:
        self.storage_path.mkdir(parents=True, exist_ok=True)
        destination = self.storage_path / f"{turn.session_id}.json"
        existing = self._read(destination) or {}
        turns = list(existing.get("turns", []))
        serialized = turn.to_dict()
        turns = [item for item in turns if item.get("turn_id") != turn.turn_id]
        turns.append(serialized)
        document = {
            "schema_version": SCHEMA_VERSION,
            "id": turn.session_id,
            "created_at": existing.get("created_at", turn.started_at.isoformat()),
            "updated_at": (turn.finished_at or turn.started_at).isoformat(),
            "current_directory": current_directory,
            "conversation_history": _sanitize_for_storage(list(conversation_history)),
            "turns": _sanitize_for_storage(turns),
        }
        temporary = destination.with_suffix(f".{os.getpid()}.tmp")
        try:
            temporary.write_text(
                json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    def restore_session(self, session_id: str) -> RestoredSession | None:
        value = self._read(self.storage_path / f"{session_id}.json")
        return self._restore(value) if value else None

    def restore_latest(self, *, current_directory: str) -> RestoredSession | None:
        if not self.storage_path.exists():
            return None
        matches: list[tuple[str, dict[str, Any]]] = []
        for path in self.storage_path.glob("*.json"):
            value = self._read(path)
            if value and value.get("current_directory") == current_directory:
                matches.append((str(value.get("updated_at", "")), value))
        return (
            self._restore(max(matches, key=lambda item: item[0])[1])
            if matches
            else None
        )

    def export_sanitized_report(self, session_id: str, destination: Path) -> Path:
        """Export the canonical, already-sanitized audit document."""
        value = self._read(self.storage_path / f"{session_id}.json")
        if value is None:
            raise FileNotFoundError(session_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return destination

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | None:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    @staticmethod
    def _restore(value: dict[str, Any]) -> RestoredSession:
        version = int(value.get("schema_version", 0))
        if version != SCHEMA_VERSION:
            raise ValueError(f"unsupported turn repository schema: {version}")
        return RestoredSession(
            session_id=str(value["id"]),
            conversation_history=[
                dict(item) for item in value.get("conversation_history", [])
            ],
            turns=[TurnExecution.from_dict(item) for item in value.get("turns", [])],
        )


__all__ = ["AtomicTurnRepository"]


def _sanitize_for_storage(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_for_storage(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_for_storage(item) for item in value]
    if isinstance(value, str):
        return _SECRET_TEXT.sub(
            lambda match: f"{match.group(1) or ''}[REDACTED]", value
        )
    return value
