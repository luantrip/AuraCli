"""Presentation-neutral inbox for work that needs human attention."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class AttentionEntry:
    key: str
    task_id: str
    title: str
    message: str
    blocking: bool = False


@dataclass(frozen=True)
class AttentionInbox:
    entries: tuple[AttentionEntry, ...] = ()

    @property
    def blocking_count(self) -> int:
        return sum(entry.blocking for entry in self.entries)


def put_attention(inbox: AttentionInbox, entry: AttentionEntry) -> AttentionInbox:
    """Insert or replace a correlated entry while preserving arrival order."""
    entries = tuple(item for item in inbox.entries if item.key != entry.key)
    return replace(inbox, entries=(*entries, entry))


def resolve_attention(inbox: AttentionInbox, key: str) -> AttentionInbox:
    """Remove a resolved attention entry. Unknown keys are harmless."""
    return replace(
        inbox, entries=tuple(item for item in inbox.entries if item.key != key)
    )


__all__ = [
    "AttentionEntry",
    "AttentionInbox",
    "put_attention",
    "resolve_attention",
]
