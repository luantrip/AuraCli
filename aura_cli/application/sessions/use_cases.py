"""Backend- and UI-neutral session use cases."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, MutableSequence, Protocol, Sequence


class SessionRepository(Protocol):
    """Persistence capabilities required by session use cases."""

    def create_session(self, name: str) -> Any: ...

    def save_session(self, session: Any) -> None: ...

    def load_session(self, session_id: str) -> Any | None: ...

    def list_sessions(self) -> Sequence[Any]: ...


class WorkspaceSessionTarget(Protocol):
    """Mutable workspace state restored by a loaded session."""

    conversation_history: MutableSequence[dict[str, Any]]
    final_model: str


@dataclass(frozen=True)
class SaveSessionOutcome:
    session_id: str
    name: str
    message_count: int


class LoadSessionStatus(str, Enum):
    LOADED = "loaded"
    NOT_FOUND = "not_found"
    AMBIGUOUS = "ambiguous"


@dataclass(frozen=True)
class LoadSessionOutcome:
    status: LoadSessionStatus
    session: Any | None = None
    matches: tuple[Any, ...] = ()
    message_count: int = 0


def count_conversation_messages(messages: Iterable[dict[str, Any]]) -> int:
    """Count conversational turns while excluding system/tool-only records."""
    return sum(
        1 for message in messages if message.get("role") in {"user", "assistant"}
    )


def save_workspace_session(
    repository: SessionRepository,
    *,
    name: str,
    conversation_history: Iterable[dict[str, Any]],
    model: str = "",
) -> SaveSessionOutcome:
    """Capture the current workspace conversation in a persistent session."""
    history = list(conversation_history)
    session = repository.create_session(name=name)
    session.conversation_history = history
    session.model = model
    repository.save_session(session)
    return SaveSessionOutcome(
        session_id=str(session.id),
        name=str(session.name),
        message_count=count_conversation_messages(history),
    )


def load_session_into_workspace(
    repository: SessionRepository,
    *,
    reference: str,
    workspace: WorkspaceSessionTarget,
) -> LoadSessionOutcome:
    """Resolve a session reference and restore its conversation into a workspace."""
    session = repository.load_session(reference)
    matches: tuple[Any, ...] = ()
    if session is None:
        matches = tuple(
            candidate
            for candidate in repository.list_sessions()
            if str(candidate.id).startswith(reference) or candidate.name == reference
        )
        if len(matches) > 1:
            return LoadSessionOutcome(
                status=LoadSessionStatus.AMBIGUOUS,
                matches=matches,
            )
        if len(matches) == 1:
            session = repository.load_session(str(matches[0].id))

    if session is None:
        return LoadSessionOutcome(status=LoadSessionStatus.NOT_FOUND)

    history = list(session.conversation_history)
    workspace.conversation_history = history
    if session.model:
        workspace.final_model = session.model
    return LoadSessionOutcome(
        status=LoadSessionStatus.LOADED,
        session=session,
        message_count=count_conversation_messages(history),
    )
