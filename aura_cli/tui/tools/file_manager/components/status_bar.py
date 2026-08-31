"""Status bar component for File Manager.

Displays file information, disk usage, and operation status.

Features:
    - Current selection information
    - Disk usage statistics
    - Operation progress
    - File preview
    - Real-time updates

Classes:
    FileManagerStatusBar: Status bar widget with file info
    FilePreview: File preview widget
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
from typing import ClassVar, Optional

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Static

from aura_cli.application.presentation.file_browser import format_file_size


class FileManagerStatusBar(Widget):
    """Status bar showing file information and disk usage."""

    DEFAULT_CSS = """
    FileManagerStatusBar {
        width: 100%;
        height: 2;
        background: $surface;
        border-top: solid $primary;
    }

    FileManagerStatusBar > Horizontal {
        width: 100%;
        height: 100%;
        padding: 0 1;
    }

    FileManagerStatusBar .status-left {
        width: 1fr;
        height: 1;
        color: $text;
    }

    FileManagerStatusBar .status-center {
        width: auto;
        height: 1;
        color: $accent;
    }

    FileManagerStatusBar .status-right {
        width: auto;
        height: 1;
        color: $muted;
        text-align: right;
    }
    """

    # Reactive properties
    selected_path: reactive[Optional[Path]] = reactive(None)
    selected_count: reactive[int] = reactive(0)
    clipboard_info: reactive[str] = reactive("")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._disk_info = ""

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield Static("Pronto", id="status-left", classes="status-left")
            yield Static("", id="status-center", classes="status-center")
            yield Static("", id="status-right", classes="status-right")

    def on_mount(self) -> None:
        """Update disk info on mount."""
        self._update_disk_info()

    def watch_selected_path(self, path: Optional[Path]) -> None:
        """Update status when selection changes."""
        self._update_file_info(path)

    def watch_selected_count(self, count: int) -> None:
        """Update status when selection count changes."""
        center = self.query_one("#status-center", Static)
        if count > 1:
            center.update(f"◫ {count} itens selecionados")
        else:
            center.update("")

    def watch_clipboard_info(self, info: str) -> None:
        """Update clipboard info."""
        if info:
            center = self.query_one("#status-center", Static)
            center.update(info)

    def _update_file_info(self, path: Optional[Path]) -> None:
        """Update the file info display."""
        left = self.query_one("#status-left", Static)

        if not path or not path.exists():
            left.update("Pronto")
            return

        try:
            stat_info = path.stat()

            if path.is_dir():
                # Count items in directory
                try:
                    items = list(path.iterdir())
                    dirs = sum(1 for p in items if p.is_dir())
                    files = len(items) - dirs
                    info = f"▷ {path.name} | {dirs} folders, {files} files"
                except PermissionError:
                    info = f"▷ {path.name} | Acesso negado"
            else:
                # Show file info
                size = format_file_size(stat_info.st_size)
                modified = datetime.fromtimestamp(stat_info.st_mtime)
                info = f"◇ {path.name} | {size} | Modified: {modified.strftime('%Y-%m-%d %H:%M')}"

            left.update(info)
        except Exception as e:
            left.update(f"Erro: {e}")

    def _update_disk_info(self, path: Optional[Path] = None) -> None:
        """Update disk usage information."""
        right = self.query_one("#status-right", Static)

        try:
            target = path or Path.home()
            usage = shutil.disk_usage(target)
            total = format_file_size(usage.total)
            free = format_file_size(usage.free)
            percent = (usage.used / usage.total) * 100

            self._disk_info = f"▾ {free} livre / {total} ({percent:.1f}% usado)"
            right.update(self._disk_info)
        except Exception:
            right.update("")

    def set_status(self, message: str) -> None:
        """Set a custom status message."""
        left = self.query_one("#status-left", Static)
        left.update(message)

    def set_operation(self, operation: str) -> None:
        """Set the current operation status."""
        center = self.query_one("#status-center", Static)
        center.update(operation)

    def clear_operation(self) -> None:
        """Clear the operation status."""
        center = self.query_one("#status-center", Static)
        center.update("")


class FilePreview(Widget):
    """Preview panel for files (shows content preview for text files)."""

    DEFAULT_CSS = """
    FilePreview {
        width: 100%;
        height: 100%;
        background: $surface;
        border: solid $primary;
    }

    FilePreview > Static {
        width: 100%;
        height: 100%;
        padding: 1;
        overflow: auto;
    }

    FilePreview .preview-header {
        width: 100%;
        height: 2;
        background: $surface;
        border-bottom: solid $primary;
        padding: 0 1;
    }

    FilePreview .preview-content {
        width: 100%;
        height: 1fr;
        overflow-y: auto;
    }

    FilePreview .no-preview {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: $muted;
    }
    """

    # Text file extensions that we can preview
    TEXT_EXTENSIONS: ClassVar[dict] = {
        ".txt",
        ".md",
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".json",
        ".yaml",
        ".yml",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".xml",
        ".html",
        ".css",
        ".scss",
        ".sass",
        ".sh",
        ".bash",
        ".zsh",
        ".fish",
        ".sql",
        ".rs",
        ".go",
        ".java",
        ".kt",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rb",
        ".php",
        ".pl",
        ".lua",
        ".vim",
        ".el",
        ".lisp",
        ".r",
        ".R",
        ".swift",
        ".scala",
        ".clj",
        ".hs",
        ".ex",
        ".exs",
        ".erl",
        ".gitignore",
        ".gitattributes",
        ".env",
        ".editorconfig",
        "Makefile",
        "Dockerfile",
        "README",
        "LICENSE",
        "CHANGELOG",
        "TODO",
        "AUTHORS",
    }

    # Maximum file size to preview (in bytes)
    MAX_PREVIEW_SIZE = 100 * 1024  # 100KB

    current_file: reactive[Optional[Path]] = reactive(None)

    def compose(self) -> ComposeResult:
        yield Static(
            "Selecione um arquivo para visualizar",
            classes="no-preview",
            id="preview-content",
        )

    def watch_current_file(self, path: Optional[Path]) -> None:
        """Update preview when file changes."""
        self._update_preview(path)

    def _update_preview(self, path: Optional[Path]) -> None:
        """Update the preview content."""
        content = self.query_one("#preview-content", Static)

        if not path:
            content.update("Selecione um arquivo para visualizar")
            content.add_class("no-preview")
            return

        if not path.exists():
            content.update("File not found")
            content.add_class("no-preview")
            return

        if path.is_dir():
            self._preview_directory(path, content)
            return

        # Check if we can preview this file
        suffix = path.suffix.lower()
        name = path.name.lower()

        if suffix not in self.TEXT_EXTENSIONS and name not in self.TEXT_EXTENSIONS:
            self._preview_binary(path, content)
            return

        # Check file size
        try:
            size = path.stat().st_size
            if size > self.MAX_PREVIEW_SIZE:
                content.update(
                    f"Arquivo muito grande para visualizar ({format_file_size(size)})"
                )
                content.add_class("no-preview")
                return
        except Exception:
            content.update("Não foi possível ler o arquivo")
            content.add_class("no-preview")
            return

        # Read and display content
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            # Limit lines
            lines = text.split("\n")[:100]
            preview_text = "\n".join(lines)
            if len(lines) == 100:
                preview_text += "\n... (truncado)"

            content.update(preview_text)
            content.remove_class("no-preview")
        except Exception as e:
            content.update(f"Error reading file: {e}")
            content.add_class("no-preview")

    def _preview_directory(self, path: Path, content: Static) -> None:
        """Preview directory contents."""
        try:
            items = sorted(
                path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )

            lines = [f"▷ {path.name}/", ""]

            for item in items[:50]:
                if item.is_dir():
                    lines.append(f"  ▷ {item.name}/")
                else:
                    size = format_file_size(item.stat().st_size)
                    lines.append(f"  ◇ {item.name:<30} {size:>10}")

            if len(list(path.iterdir())) > 50:
                lines.append(f"\n  ... e mais {len(list(path.iterdir())) - 50} itens")

            content.update("\n".join(lines))
            content.remove_class("no-preview")
        except PermissionError:
            content.update("Permissão negada")
            content.add_class("no-preview")

    def _preview_binary(self, path: Path, content: Static) -> None:
        """Show info for binary files."""
        try:
            stat_info = path.stat()
            size = format_file_size(stat_info.st_size)
            modified = datetime.fromtimestamp(stat_info.st_mtime)

            # Determine file type
            suffix = path.suffix.lower()
            if suffix in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".ico"}:
                icon = "◇ Imagem"
            elif suffix in {".mp3", ".wav", ".flac", ".m4a", ".ogg", ".aac"}:
                icon = "♪ Áudio"
            elif suffix in {".mp4", ".mkv", ".avi", ".mov", ".webm"}:
                icon = "▶ Vídeo"
            elif suffix in {".zip", ".tar", ".gz", ".rar", ".7z"}:
                icon = "◇ Arquivo compactado"
            elif suffix in {".pdf"}:
                icon = "◇ Documento PDF"
            elif suffix in {".exe", ".msi", ".dmg", ".app"}:
                icon = "◎ Executável"
            else:
                icon = "◇ Binary File"

            info = [
                f"{icon}",
                "",
                f"Nome: {path.name}",
                f"Tamanho: {size}",
                f"Modificado: {modified.strftime('%Y-%m-%d %H:%M:%S')}",
                "",
                "(Arquivo binário - visualização não disponível)",
            ]

            content.update("\n".join(info))
            content.add_class("no-preview")
        except Exception as e:
            content.update(f"Erro: {e}")
            content.add_class("no-preview")
