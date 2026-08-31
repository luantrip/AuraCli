"""Presentation-neutral policy for routing output across TUI surfaces."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SurfaceKind(str, Enum):
    CONVERSATION = "conversation"
    ACTIVITY = "activity"
    NOTIFICATION = "notification"
    BLOCKING = "blocking"
    TOOL = "tool"


class PresentationIntent(str, Enum):
    RESPONSE = "response"
    INFORMATION = "information"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    PROGRESS = "progress"
    TOOL_RESULT = "tool_result"
    TOOL_OPEN = "tool_open"
    DECISION = "decision"


class SurfacePriority(str, Enum):
    PASSIVE = "passive"
    NORMAL = "normal"
    ATTENTION = "attention"
    BLOCKING = "blocking"


@dataclass(frozen=True)
class SurfaceRequest:
    intent: PresentationIntent
    content: str
    title: str | None = None
    persistent: bool = False
    task_id: str = "global_chat"
    route: str | None = None
    key: str | None = None
    tone: str | None = None
    replace: bool = False
    consolidate: bool = False
    elapsed_seconds: int | None = None
    heartbeat_due: bool = False
    background: bool = False
    resolves_attention: bool = False


@dataclass(frozen=True)
class SurfaceDecision:
    primary: SurfaceKind
    mirrors: tuple[SurfaceKind, ...] = ()
    priority: SurfacePriority = SurfacePriority.NORMAL
    persistent: bool = False
    reveal: bool = False

    @property
    def destinations(self) -> tuple[SurfaceKind, ...]:
        return (self.primary, *self.mirrors)


def decide_surface(request: SurfaceRequest) -> SurfaceDecision:
    """Route output by meaning, not by whichever adapter emitted it."""
    intent = request.intent
    if intent is PresentationIntent.RESPONSE:
        return SurfaceDecision(SurfaceKind.CONVERSATION, persistent=True)
    if intent in (PresentationIntent.INFORMATION, PresentationIntent.TOOL_RESULT):
        return SurfaceDecision(
            SurfaceKind.CONVERSATION,
            persistent=request.persistent or intent is PresentationIntent.TOOL_RESULT,
        )
    if intent is PresentationIntent.SUCCESS:
        return SurfaceDecision(
            SurfaceKind.NOTIFICATION, priority=SurfacePriority.PASSIVE
        )
    if intent is PresentationIntent.PROGRESS:
        return SurfaceDecision(SurfaceKind.ACTIVITY, priority=SurfacePriority.PASSIVE)
    if intent is PresentationIntent.TOOL_OPEN:
        return SurfaceDecision(SurfaceKind.TOOL, reveal=True)
    if intent is PresentationIntent.WARNING:
        return SurfaceDecision(
            SurfaceKind.NOTIFICATION,
            mirrors=(SurfaceKind.ACTIVITY,),
            priority=SurfacePriority.ATTENTION,
        )
    if intent is PresentationIntent.ERROR:
        mirrors = (
            (SurfaceKind.CONVERSATION,)
            if request.persistent
            else (SurfaceKind.ACTIVITY,)
        )
        return SurfaceDecision(
            SurfaceKind.NOTIFICATION,
            mirrors=mirrors,
            priority=SurfacePriority.ATTENTION,
            persistent=request.persistent,
        )
    if intent is PresentationIntent.DECISION:
        return SurfaceDecision(
            SurfaceKind.BLOCKING,
            priority=SurfacePriority.BLOCKING,
            reveal=True,
        )
    raise ValueError(f"Unsupported presentation intent: {intent}")


__all__ = [
    "PresentationIntent",
    "SurfaceDecision",
    "SurfaceKind",
    "SurfacePriority",
    "SurfaceRequest",
    "decide_surface",
]
