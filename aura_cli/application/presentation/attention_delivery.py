"""Policy for escalating relevant work beyond the currently focused surface."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum

from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)


class AttentionChannel(str, Enum):
    IN_APP = "in_app"
    TERMINAL_TITLE = "terminal_title"
    BELL = "bell"


@dataclass(frozen=True)
class AttentionPreferences:
    awaiting_user: bool = True
    failures: bool = True
    completions: bool = True
    terminal_title: bool = True
    audible_bell: bool = False


@dataclass(frozen=True)
class AttentionDelivery:
    key: str
    message: str
    channels: tuple[AttentionChannel, ...]
    terminal_title: str | None


@dataclass(frozen=True)
class AttentionDeliveryState:
    signatures: frozenset[str] = frozenset()


def resolve_attention_delivery(
    state: AttentionDeliveryState,
    request: SurfaceRequest,
) -> AttentionDeliveryState:
    """Forget dedupe signatures for a task after its attention is resolved."""
    if not request.resolves_attention:
        return state
    key = request.key or request.task_id
    prefix = f"{key}:"
    return replace(
        state,
        signatures=frozenset(
            signature
            for signature in state.signatures
            if not signature.startswith(prefix)
        ),
    )


def decide_attention_delivery(
    state: AttentionDeliveryState,
    request: SurfaceRequest,
    *,
    focused_task_id: str | None,
    app_focused: bool,
    preferences: AttentionPreferences = AttentionPreferences(),
) -> tuple[AttentionDeliveryState, AttentionDelivery | None]:
    """Escalate only meaningful off-focus transitions and deduplicate them."""
    category = _category(request)
    if category is None or not _enabled(category, preferences):
        return state, None
    outside_task = bool(
        focused_task_id and request.task_id not in {focused_task_id, "global_chat"}
    )
    if app_focused and not outside_task and not request.background:
        return state, None
    key = request.key or request.task_id
    signature = f"{key}:{category}"
    if signature in state.signatures:
        return state, None
    channels = [AttentionChannel.IN_APP]
    title = None
    if preferences.terminal_title:
        channels.append(AttentionChannel.TERMINAL_TITLE)
        title = f"Aura · {_title(category)}"
    if preferences.audible_bell:
        channels.append(AttentionChannel.BELL)
    return (
        replace(state, signatures=frozenset((*state.signatures, signature))),
        AttentionDelivery(key, request.content, tuple(channels), title),
    )


def _category(request: SurfaceRequest) -> str | None:
    if request.intent is PresentationIntent.DECISION:
        return "awaiting"
    if request.intent is PresentationIntent.ERROR:
        return "failure"
    if request.tone == "success" and request.consolidate:
        return "completion"
    return None


def _enabled(category: str, preferences: AttentionPreferences) -> bool:
    return {
        "awaiting": preferences.awaiting_user,
        "failure": preferences.failures,
        "completion": preferences.completions,
    }[category]


def _title(category: str) -> str:
    return {
        "awaiting": "ação necessária",
        "failure": "falha",
        "completion": "completed",
    }[category]


__all__ = [
    "AttentionChannel",
    "AttentionDelivery",
    "AttentionDeliveryState",
    "AttentionPreferences",
    "decide_attention_delivery",
    "resolve_attention_delivery",
]
