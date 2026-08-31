"""Immutable keyed feed for flicker-free operational activity updates."""

from __future__ import annotations

from dataclasses import dataclass, replace

from aura_cli.application.presentation.tui_surfaces import SurfaceRequest


def _effective_activity_request(request: SurfaceRequest) -> SurfaceRequest:
    """Give legacy activity producers a stable correlation key."""
    if request.key:
        return request
    key = ":".join(
        (
            "implicit",
            request.task_id or "global_chat",
            request.intent.value,
            request.route or "activity",
            request.title or "untitled",
        )
    )
    return replace(request, key=key)


@dataclass(frozen=True)
class ActivityFeed:
    active: tuple[SurfaceRequest, ...] = ()
    completed: tuple[SurfaceRequest, ...] = ()


def reduce_activity(feed: ActivityFeed, request: SurfaceRequest) -> ActivityFeed:
    """Replace one live row or consolidate its final state exactly once."""
    request = _effective_activity_request(request)
    key = request.key
    active = tuple(item for item in feed.active if item.key != key)
    completed = tuple(item for item in feed.completed if item.key != key)
    if request.consolidate:
        return replace(feed, active=active, completed=(*completed, request))
    if request.replace:
        return replace(feed, active=(*active, request), completed=completed)
    return replace(feed, active=active, completed=(*completed, request))


__all__ = ["ActivityFeed", "reduce_activity"]
