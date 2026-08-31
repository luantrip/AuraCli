"""Choose the execution route for free-form presentation input."""

from __future__ import annotations

from enum import Enum
from typing import Protocol

from aura_cli.application.presentation.codebase_analysis import (
    requests_codebase_investigation,
)


class AgiIntentRouter(Protocol):
    def should_use_agi_worker(self, command: str) -> bool: ...


class PresentationInputRoute(Enum):
    CODEBASE_INVESTIGATION = "codebase_investigation"
    AGI_WORKER = "agi_worker"
    DIRECT = "direct"
    UNAVAILABLE = "unavailable"


def route_presentation_input(
    command: str, *, router: AgiIntentRouter, runtime_available: bool
) -> PresentationInputRoute:
    """Select one mutually exclusive execution route in priority order."""
    if not runtime_available:
        return PresentationInputRoute.UNAVAILABLE
    if requests_codebase_investigation(command):
        return PresentationInputRoute.CODEBASE_INVESTIGATION
    if router.should_use_agi_worker(command):
        return PresentationInputRoute.AGI_WORKER
    return PresentationInputRoute.DIRECT


__all__ = ["AgiIntentRouter", "PresentationInputRoute", "route_presentation_input"]
