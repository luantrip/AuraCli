"""Timing policy for rate-limited worker status publication."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StatusThrottle:
    """Decide whether a status may be emitted at a given monotonic timestamp."""

    interval: float = 0.5
    last_emitted_at: float | None = None

    def allow(self, now: float) -> bool:
        """Accept the first event and later events separated by ``interval``."""
        if self.interval < 0:
            raise ValueError("Status throttle interval cannot be negative")
        if (
            self.last_emitted_at is not None
            and now - self.last_emitted_at < self.interval
        ):
            return False
        self.last_emitted_at = now
        return True

    def reset(self) -> None:
        """Allow the next status immediately."""
        self.last_emitted_at = None
