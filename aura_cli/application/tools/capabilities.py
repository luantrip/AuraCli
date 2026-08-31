"""Neutral capability metadata shared by tool runtimes.

This module intentionally depends only on the standard library so application
policy code can consume metadata without importing the core registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ToolCapability:
    """Execution metadata for one public tool name."""

    name: str
    effect: str = "read_only"
    risk: str = "low"
    retryable: bool = False
    runtimes: frozenset[str] = field(default_factory=lambda: frozenset({"general"}))

    @property
    def mutating(self) -> bool:
        """Whether the capability may change state or cause an external effect."""
        return self.effect.casefold() not in {"read_only", "readonly", "read-only"}


class CapabilityMatrix:
    """Deterministic lookup and runtime filtering for tool capabilities."""

    def __init__(self, capabilities: Iterable[ToolCapability] = ()) -> None:
        entries = list(capabilities)
        names = [entry.name for entry in entries]
        if len(names) != len(set(names)):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            raise ValueError(f"Duplicated capability names: {', '.join(duplicates)}")
        self._entries = {entry.name: entry for entry in entries}

    def get(self, name: str) -> ToolCapability | None:
        """Return metadata for a tool name, or ``None`` when unknown."""
        return self._entries.get(name)

    def require(self, name: str) -> ToolCapability:
        """Return metadata or raise an explicit unknown-capability error."""
        capability = self.get(name)
        if capability is None:
            raise KeyError(f"Unknown tool capability: {name}")
        return capability

    def for_runtime(self, runtime: str) -> tuple[ToolCapability, ...]:
        """Return stable name-sorted capabilities available to one runtime."""
        return tuple(
            sorted(
                (
                    entry
                    for entry in self._entries.values()
                    if runtime in entry.runtimes
                ),
                key=lambda entry: entry.name,
            )
        )

    def as_dict(self) -> dict[str, dict[str, Any]]:
        """Return a JSON-safe snapshot for diagnostics and catalogs."""
        return {
            name: {
                "effect": entry.effect,
                "risk": entry.risk,
                "retryable": entry.retryable,
                "runtimes": sorted(entry.runtimes),
            }
            for name, entry in sorted(self._entries.items())
        }

    @classmethod
    def from_mappings(cls, entries: Iterable[Mapping[str, Any]]) -> CapabilityMatrix:
        """Build a matrix from manifest-like mappings without importing them."""
        capabilities: list[ToolCapability] = []
        for entry in entries:
            effect = str(entry.get("effect", "read_only"))
            declared_risk = entry.get("risk")
            risk = (
                str(declared_risk)
                if declared_risk is not None
                else ("low" if effect == "read_only" else "medium")
            )
            capabilities.append(
                ToolCapability(
                    name=str(entry["name"]),
                    effect=effect,
                    risk=risk,
                    retryable=bool(entry.get("retryable", False)),
                    runtimes=frozenset(
                        str(runtime) for runtime in entry.get("runtimes", ("general",))
                    ),
                )
            )
        return cls(capabilities)


__all__ = ["CapabilityMatrix", "ToolCapability"]
