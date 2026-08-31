"""Machine-readable deprecation schedule for the public ADK."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Deprecation:
    replacement: str
    deprecated_since: str
    remove_no_earlier_than: str


DEPRECATIONS = {
    "MemoryStore": Deprecation(
        replacement="PersistentMemory",
        deprecated_since="0.2.0",
        remove_no_earlier_than="1.0.0",
    )
}

__all__ = ["DEPRECATIONS", "Deprecation"]
