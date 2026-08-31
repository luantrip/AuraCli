"""Framework-neutral presentation decisions for content monitors."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence


class MonitorContentMode(Enum):
    EMPTY = "empty"
    LOADING = "loading"
    ERROR = "error"
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"


@dataclass(frozen=True)
class MonitorContentView:
    mode: MonitorContentMode
    content: str


@dataclass(frozen=True)
class MonitorAddressView:
    url: str
    secure: bool
    can_back: bool
    can_forward: bool
    loading: bool
    status: str


@dataclass(frozen=True)
class MonitorTabView:
    index: int
    label: str
    active: bool


@dataclass(frozen=True)
class MonitorHealthView:
    status: str
    preview: str


def normalize_monitor_url(value: str) -> str:
    """Normalize an address or local path without performing I/O."""
    value = value.strip()
    if value.startswith(("http://", "https://", "file://", "about:")):
        return value
    if "." in value and not value.startswith("/"):
        return f"https://{value}"
    return f"file://{value}"


def build_content_view(
    content: str,
    content_type: str = "text/plain",
    *,
    loading: bool = False,
    error: str = "",
) -> MonitorContentView:
    if loading:
        return MonitorContentView(MonitorContentMode.LOADING, "⟳ Loading...")
    if error:
        return MonitorContentView(MonitorContentMode.ERROR, f"✗ {error}")
    if not content:
        return MonitorContentView(MonitorContentMode.EMPTY, "No content to display")
    modes = {
        "application/json": MonitorContentMode.JSON,
        "text/markdown": MonitorContentMode.MARKDOWN,
    }
    return MonitorContentView(modes.get(content_type, MonitorContentMode.TEXT), content)


def build_address_view(tab: Any) -> MonitorAddressView:
    """Project the duck-typed browser tab used by concrete monitor adapters."""
    url = str(getattr(tab, "url", ""))
    title = str(getattr(tab, "title", ""))
    return MonitorAddressView(
        url=url,
        secure=url.startswith("https://"),
        can_back=bool(tab.can_go_back()),
        can_forward=bool(tab.can_go_forward()),
        loading=bool(getattr(tab, "loading", False)),
        status=title or url,
    )


def build_tab_views(tabs: Sequence[Any], active_index: int) -> list[MonitorTabView]:
    views = []
    for index, tab in enumerate(tabs):
        title = str(getattr(tab, "title", "")) or "New Tab"
        label = (
            f"{'● ' if getattr(tab, 'loading', False) else ''}{_truncate(title, 15)}"
        )
        views.append(MonitorTabView(index, label, index == active_index))
    return views


def build_health_view(content: Any) -> MonitorHealthView:
    if bool(getattr(content, "is_error", False)):
        return MonitorHealthView("error", f"Error: {getattr(content, 'error', '')}")
    text = getattr(content, "text", "")
    rendered = text if isinstance(text, str) else str(text) if text else ""
    return MonitorHealthView("ok", "\n".join(rendered.splitlines()[:3])[:200])


def _truncate(value: str, limit: int) -> str:
    return value[: limit - 3] + "..." if len(value) > limit else value


__all__ = [
    "MonitorAddressView",
    "MonitorContentMode",
    "MonitorContentView",
    "MonitorHealthView",
    "MonitorTabView",
    "build_address_view",
    "build_content_view",
    "build_health_view",
    "build_tab_views",
    "normalize_monitor_url",
]
