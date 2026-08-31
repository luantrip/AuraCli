"""Imagination Panel - Holographic Project Structure Visualization.

Sci-fi inspired TUI widget providing real-time project structure visualization
with futuristic aesthetics using high-performance Imagination Engine (Nim-based).
"""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from textual.containers import Grid, Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, Static, Tree
from textual.worker import Worker

from aura_cli.core.tools.imagination_tools import (
    FileCategory,
    FileInfo,
    ScanOptions,
    ScanResult,
    get_imagination_scanner,
)


class ScanStatus(Enum):
    """Status of the scanning process."""

    IDLE = "idle"
    SCANNING = "scanning"
    WATCHING = "watching"
    ERROR = "error"


@dataclass
class ActivityEvent:
    """Represents a file activity event."""

    timestamp: datetime
    action: str
    file_path: str
    category: FileCategory


SCAN_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

CATEGORY_ICONS = {
    FileCategory.CODE: "◈",
    FileCategory.CONFIG: "◉",
    FileCategory.DOC: "◎",
    FileCategory.STYLE: "◐",
    FileCategory.DATA: "◧",
    FileCategory.BINARY: "◆",
    FileCategory.OTHER: "○",
}


class HolographicHeader(Static):
    """Animated holographic header with scan line effect."""

    scan_frame = reactive(0)
    status = reactive(ScanStatus.IDLE)

    def __init__(self, title: str = "IMAGINATION ENGINE", **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.title = title

    def compose(self):
        """Compose header structure."""
        with Horizontal():
            yield Label("▐", classes="border-left")
            yield Label("", id="scan-indicator", classes="scan-indicator")
            yield Label(self.title, classes="title")
            yield Label("", id="status", classes="status-idle")

    def on_mount(self) -> None:
        """Start animation on mount."""
        self.set_interval(0.1, self._animate)

    def _animate(self) -> None:  # type: ignore[override]
        """Animate the scan indicator."""
        if self.status == ScanStatus.SCANNING:
            self.scan_frame = (self.scan_frame + 1) % len(SCAN_FRAMES)
            indicator = self.query_one("#scan-indicator", Label)
            indicator.update(SCAN_FRAMES[self.scan_frame])

    def watch_status(self, status: ScanStatus) -> None:
        """Update status display when status changes."""
        status_label = self.query_one("#status", Label)
        indicator = self.query_one("#scan-indicator", Label)

        status_label.remove_class(
            "status-idle", "status-scanning", "status-watching", "status-error"
        )
        indicator.remove_class(
            "status-idle", "status-scanning", "status-watching", "status-error"
        )

        if status == ScanStatus.SCANNING:
            status_label.update("SCANNING")
            status_label.add_class("status-scanning")
            indicator.update(SCAN_FRAMES[self.scan_frame])
        elif status == ScanStatus.WATCHING:
            status_label.update("LIVE")
            status_label.add_class("status-watching")
            indicator.update("◉")
        elif status == ScanStatus.ERROR:
            status_label.update("ERROR")
            status_label.add_class("status-error")
            indicator.update("✖")
        else:
            status_label.update("STANDBY")
            status_label.add_class("status-idle")
            indicator.update("◇")


class CategoryBreakdown(Static):
    """Visual breakdown of file categories with holographic bars."""

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.data: Dict[str, int] = {}

    def compose(self):
        """Compose category breakdown structure."""
        yield Static("", id="category-content")

    def update_data(self, data: Dict[str, int]) -> None:
        """Update category data."""
        self.data = data
        self._update_display()

    def _update_display(self) -> None:
        """Update the visual display."""
        content = self.query_one("#category-content", Static)

        if not self.data:
            content.update("Sem dados disponíveis")
            return

        total = sum(self.data.values())
        max_val = max(self.data.values()) if self.data else 1
        bar_width = 30

        lines = []
        for cat_name, count in sorted(self.data.items(), key=lambda x: -x[1]):
            if count == 0:
                continue

            try:
                category = FileCategory(cat_name)
                icon = CATEGORY_ICONS.get(category, "○")
            except ValueError:
                icon = "○"

            bar_len = int((count / max_val) * bar_width)
            bar_filled = "█" * bar_len
            bar_empty = "░" * (bar_width - bar_len)
            pct = (count / total * 100) if total > 0 else 0

            lines.append(
                f" {icon} {cat_name:8} {bar_filled}{bar_empty} {count:4} ({pct:4.1f}%)"
            )

        content.update("\n".join(lines))


class RecentActivity(Static):
    """Real-time activity stream with holographic styling."""

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.activities: List[FileInfo] = []
        self.max_items = 15

    def compose(self):
        """Compose activity stream structure."""
        yield Label("◉ ATIVIDADE RECENTE", classes="activity-header")
        yield Static("", id="activity-content")

    def update_activities(self, files: List[FileInfo]) -> None:
        """Update recent activities."""
        self.activities = files[: self.max_items]
        self._update_display()

    def _update_display(self) -> None:
        """Update the visual display."""
        content = self.query_one("#activity-content", Static)

        if not self.activities:
            content.update("Sem atividade recente")
            return

        lines = []
        for f in self.activities:
            try:
                icon = CATEGORY_ICONS.get(f.category, "○")
            except (TypeError, ValueError):
                icon = "○"

            name = f.name
            if len(name) > 25:
                name = name[:22] + "..."

            lines.append(f"{icon} {name:25} {f.age_human:>10}")

        content.update("\n".join(lines))


class ExtensionCloud(Static):
    """Visual cloud of file extensions."""

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.extensions: Dict[str, int] = {}

    def compose(self):
        """Compose extension cloud structure."""
        yield Static("", id="extension-content")

    def update_data(self, data: Dict[str, int]) -> None:
        """Update extension data."""
        self.extensions = dict(sorted(data.items(), key=lambda x: -x[1])[:15])
        self._update_display()

    def _update_display(self) -> None:
        """Update the visual display."""
        content = self.query_one("#extension-content", Static)

        if not self.extensions:
            content.update("Nenhuma extensão encontrada")
            return

        items = []

        for ext, count in self.extensions.items():
            items.append(f"{ext}:{count}")

        content.update(" ".join(items))


class ScanStats(Static):
    """Quick scan statistics with holographic display."""

    def __init__(self, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.stats: Optional[ScanResult] = None

    def compose(self):
        """Compose stats structure."""
        yield Static("", id="stats-content")

    def update_stats(self, result: ScanResult) -> None:
        """Update statistics."""
        self.stats = result
        self._update_display()

    def _update_display(self) -> None:
        """Update the visual display."""
        content = self.query_one("#stats-content", Static)

        if not self.stats:
            content.update("Aguardando varredura...")
            return

        stats_text = (
            f"▷ Files: {self.stats.total_files:,}  │  "
            f"▷ Dirs: {self.stats.total_directories:,}  │  "
            f"✎ Lines: {self.stats.total_lines:,}  │  "
            f"▾ Size: {self.stats.total_size_human}  │  "
            f"▶ Scan: {self.stats.scan_duration_ms}ms"
        )

        content.update(stats_text)


class ImaginationPanel(Vertical):
    """Main Imagination Panel widget.

    Provides a holographic project view. The Watch control is deliberately
    implemented as bounded polling because the scanner exposes scans, not a
    filesystem-event subscription API.
    """

    WATCH_INTERVAL_SECONDS = 5.0
    status = reactive(ScanStatus.IDLE)
    scan_result: reactive[Optional[ScanResult]] = reactive(None)

    class ScanStarted(Message):
        """Emitted when scan starts."""

    class ScanCompleted(Message):
        """Emitted when scan completes."""

        def __init__(self, result: ScanResult):
            """Initialize the instance."""
            super().__init__()
            self.result = result

    class ScanError(Message):
        """Emitted on scan error."""

        def __init__(self, error: str):
            """Initialize the instance."""
            super().__init__()
            self.error = error

    def __init__(self, target_path: str = ".", **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.target_path = Path(target_path).resolve()
        self.scanner = get_imagination_scanner()
        self._scan_worker: Optional[Worker] = None
        self._watch_task: Optional[asyncio.Task] = None
        self._watch_timer: Optional[Any] = None
        self._auto_refresh: bool = False

    def compose(self):
        """Compose the panel layout."""
        yield HolographicHeader(id="imag_header", classes="imag-header")

        with Grid(classes="imag-content"):
            with Vertical(classes="imag-left-pane"):
                yield ScanStats(id="scan_stats")
                yield Static("◈ FILE CATEGORIES", classes="section-header")
                yield CategoryBreakdown(id="category_breakdown")
                yield Static("◈ EXTENSIONS", classes="section-header")
                yield ExtensionCloud(id="extension_cloud")
                yield Static("◈ FILE STRUCTURE", classes="section-header")
                yield Tree("Project", id="file_tree")

            with Vertical(classes="imag-right-pane"):
                yield RecentActivity(id="recent_activity")

        with Horizontal(classes="imag-footer"):
            yield Button("▶ Varredura", id="btn_scan", variant="primary")
            yield Button("◉ Monitorar", id="btn_watch", variant="default")
            yield Button("⟳ Atualizar", id="btn_refresh", variant="default")

    def on_mount(self) -> None:
        """Initialize on mount."""
        self.run_scan()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn_scan":
            self.run_scan()
        elif button_id == "btn_watch":
            self.toggle_watch()
        elif button_id == "btn_refresh":
            self.run_scan(use_cache=False)

    def run_scan(self, use_cache: bool = True) -> None:
        """Run a filesystem scan."""
        if self.status == ScanStatus.SCANNING:
            return

        self.status = ScanStatus.SCANNING
        self._update_header_status()
        self.post_message(self.ScanStarted())

        self.run_worker(self._do_scan(use_cache))

    async def _do_scan(self, use_cache: bool = True) -> None:
        """Perform the actual scan."""
        try:
            options = ScanOptions(
                include_preview=True, include_hidden=False, respect_gitignore=True
            )

            result = await self.scanner.scan_async(
                self.target_path, options, use_cache=use_cache
            )

            self.scan_result = result
            self.status = (
                ScanStatus.IDLE if not self._auto_refresh else ScanStatus.WATCHING
            )
            self._update_ui(result)
            self.post_message(self.ScanCompleted(result))

        except Exception as e:
            self.status = ScanStatus.ERROR
            self.post_message(self.ScanError(str(e)))
            self.notify(f"Erro na varredura: {e}", severity="error")

        self._update_header_status()

    def _update_header_status(self) -> None:
        """Update header status indicator."""
        header = self.query_one("#imag_header", HolographicHeader)
        header.status = self.status

    def _update_ui(self, result: ScanResult) -> None:
        """Update all UI components with scan result."""
        stats = self.query_one("#scan_stats", ScanStats)
        stats.update_stats(result)

        categories = self.query_one("#category_breakdown", CategoryBreakdown)
        categories.update_data(result.by_category)

        extensions = self.query_one("#extension_cloud", ExtensionCloud)
        extensions.update_data(result.by_extension)

        tree = self.query_one("#file_tree", Tree)
        tree.clear()
        root = tree.root
        root.label = "Project"
        root.expand()

        for file_info in result.files[:100]:
            try:
                icon = CATEGORY_ICONS.get(file_info.category, "○")
            except (TypeError, ValueError):
                icon = "○"

            node = root.add(f"{icon} {file_info.name}", data=file_info)
            if file_info.is_directory:
                node.expand()

        activity = self.query_one("#recent_activity", RecentActivity)
        activity.update_activities(result.files[:15])

    def toggle_watch(self) -> None:
        """Toggle bounded polling mode for refreshed project scans."""
        if self._auto_refresh:
            self._stop_watch()
            return

        self._auto_refresh = True
        self.status = ScanStatus.WATCHING
        self._watch_timer = self.set_interval(
            self.WATCH_INTERVAL_SECONDS, self._refresh_watch
        )
        self._update_header_status()
        # Refresh immediately so entering Watch never presents stale data.
        self.run_scan(use_cache=False)

    def _refresh_watch(self) -> None:
        """Refresh the project snapshot when no scan is already running."""
        if self._auto_refresh and self.status != ScanStatus.SCANNING:
            self.run_scan(use_cache=False)

    def _stop_watch(self) -> None:
        """Stop Watch polling safely and restore the idle presentation."""
        self._auto_refresh = False
        if self._watch_timer is not None:
            with contextlib.suppress(Exception):
                self._watch_timer.stop()
            self._watch_timer = None
        if self.status != ScanStatus.SCANNING:
            self.status = ScanStatus.IDLE
        self._update_header_status()

    def on_unmount(self) -> None:
        """Stop polling before the panel is detached from the application."""
        self._stop_watch()


class ImaginationCompact(Static):
    """Compact version of Imagination Panel for smaller spaces."""

    def compose(self):
        """Compose compact structure."""
        yield ScanStats(id="compact_stats")
        yield CategoryBreakdown(id="compact_categories")

    def update_data(self, result: ScanResult) -> None:
        """Update with scan result."""
        stats = self.query_one("#compact_stats", ScanStats)
        stats.update_stats(result)

        categories = self.query_one("#compact_categories", CategoryBreakdown)
        categories.update_data(result.by_category)
