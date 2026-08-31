"""Ports and records for canonical, restorable conversational turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence

from aura_cli.application.execution import TurnExecution

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RestoredSession:
    session_id: str
    conversation_history: list[dict[str, Any]]
    turns: list[TurnExecution]

    @property
    def last_turn(self) -> TurnExecution | None:
        return self.turns[-1] if self.turns else None


class TurnRepository(Protocol):
    def persist_turn(
        self,
        turn: TurnExecution,
        conversation_history: Sequence[dict[str, Any]],
        *,
        current_directory: str,
    ) -> None: ...

    def restore_session(self, session_id: str) -> RestoredSession | None: ...

    def restore_latest(self, *, current_directory: str) -> RestoredSession | None: ...


__all__ = ["SCHEMA_VERSION", "RestoredSession", "TurnRepository"]
