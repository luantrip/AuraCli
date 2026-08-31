"""In-memory extension registry independent of UI and global statistics."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Sequence


class ExtensionStatus(Enum):
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    UNLOADED = "unloaded"


@dataclass
class ExtensionInfo:
    name: str
    version: str
    status: ExtensionStatus
    metadata: dict[str, Any] = field(default_factory=dict)


class ExtensionRegistry:
    """Track extension identity and lifecycle status for the current process."""

    def __init__(
        self,
        *,
        presenter: Optional[Callable[[Sequence[ExtensionInfo]], None]] = None,
    ) -> None:
        self.extensions: dict[str, ExtensionInfo] = {}
        self._presenter = presenter

    def register(
        self, name: str, version: str, metadata: Optional[dict[str, Any]] = None
    ) -> ExtensionInfo:
        info = ExtensionInfo(
            name=name,
            version=version,
            status=ExtensionStatus.LOADED,
            metadata=metadata or {},
        )
        self.extensions[name] = info
        return info

    def set_status(self, name: str, status: ExtensionStatus) -> bool:
        info = self.extensions.get(name)
        if info is None:
            return False
        info.status = status
        return True

    def get_extension(self, name: str) -> Optional[ExtensionInfo]:
        return self.extensions.get(name)

    def list_extensions(
        self, status: Optional[ExtensionStatus] = None
    ) -> list[ExtensionInfo]:
        items = list(self.extensions.values())
        return (
            items
            if status is None
            else [item for item in items if item.status is status]
        )

    def get_statistics(self) -> dict[str, Any]:
        return {
            "total_extensions": len(self.extensions),
            "by_status": {
                status.value: sum(
                    1 for item in self.extensions.values() if item.status is status
                )
                for status in ExtensionStatus
            },
        }

    def display_registry(self) -> None:
        """Present the registry when a host presenter was configured."""
        if self._presenter is not None:
            self._presenter(
                sorted(self.extensions.values(), key=lambda item: item.name)
            )
