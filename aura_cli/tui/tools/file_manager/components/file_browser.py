"""File browser component for File Manager.

Core file browser widget with rich functionality.

Features:
    - Directory tree navigation with lazy loading
    - Rich file icons based on file type
    - File operations (copy, move, delete, rename)
    - Context menu support
    - External editor integration
    - File properties and metadata
    - Keyboard shortcuts

Classes:
    FileBrowser: Main file browser widget
    FileContextMenu: Context menu for operations
    RenameDialog: File rename dialog
    NewFileDialog: New file creation dialog
    ConfirmDialog: Confirmation dialog
    PropertiesDialog: File properties dialog
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, ClassVar, Dict, List, Optional, Set, Tuple

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Button, Static, Tree
from textual.widgets._tree import TreeNode

from aura_cli.application.presentation.file_browser import (
    append_navigation_path,
    format_file_permissions,
    format_file_size,
    plan_duplicate_destination,
    plan_transfer_destination,
)
from aura_cli.tui.components.shared.dialogs import ConfirmDialog as SharedConfirmDialog
from aura_cli.tui.tools.file_manager.components.dialogs import (
    FileContextMenu,
    NewFileDialog,
    PropertiesDialog,
    RenameDialog,
)
from aura_cli.tui.tools.file_manager.file_operations import (
    create_path,
    delete_path,
    duplicate_file,
    rename_path,
    transfer_path,
)
from aura_cli.tui.tools.integrations import is_paint_compatible
from aura_cli.tui.tools.integrations.paint_integration import OpenInPaint

format_size = format_file_size
format_permissions = format_file_permissions


# ═══════════════════════════════════════════════════════════════════════════════
# File Icons - Inspired by TUIFIProfile but simplified for Textual
# ═══════════════════════════════════════════════════════════════════════════════

FILE_ICONS: Dict[str, Tuple[str, str]] = {
    # Special keys
    "folder": ("▷", "yellow"),
    "folder_open": ("▽", "yellow"),
    "file": ("◇", "white"),
    "symlink": ("↗", "cyan"),
    "hidden": ("◌", "dim"),
    # Languages
    ".py": ("◇", "green"),
    ".js": ("◇", "yellow"),
    ".ts": ("◇", "blue"),
    ".jsx": ("◎", "cyan"),
    ".tsx": ("◎", "blue"),
    ".html": ("◇", "red"),
    ".css": ("◇", "magenta"),
    ".rs": ("◇", "red"),
    ".go": ("◇", "cyan"),
    ".java": ("◇", "red"),
    ".rb": ("◇", "red"),
    ".c": ("◆", "blue"),
    ".h": ("◆", "blue"),
    ".cpp": ("◆", "blue"),
    ".hpp": ("◆", "blue"),
    # Shell
    ".sh": ("▶", "green"),
    ".bash": ("▶", "green"),
    ".zsh": ("▶", "green"),
    ".fish": ("▶", "green"),
    ".bat": ("▶", "yellow"),
    ".cmd": ("▶", "yellow"),
    ".ps1": ("▶", "blue"),
    # Config
    ".json": ("◎", "yellow"),
    ".yaml": ("◎", "red"),
    ".yml": ("◎", "red"),
    ".toml": ("◎", "red"),
    ".ini": ("◎", "dim"),
    ".cfg": ("◎", "dim"),
    ".conf": ("◎", "dim"),
    ".env": ("◎", "yellow"),
    # Data
    ".sql": ("▥", "cyan"),
    ".db": ("▥", "cyan"),
    ".sqlite": ("▥", "cyan"),
    ".csv": ("▥", "green"),
    # Docs
    ".md": ("◇", "white"),
    ".txt": ("◇", "white"),
    ".rst": ("◇", "white"),
    ".pdf": ("◇", "red"),
    ".doc": ("◇", "blue"),
    ".docx": ("◇", "blue"),
    # Images
    ".png": ("◇", "magenta"),
    ".jpg": ("◇", "magenta"),
    ".jpeg": ("◇", "magenta"),
    ".gif": ("◇", "magenta"),
    ".svg": ("◇", "magenta"),
    ".ico": ("◇", "magenta"),
    # Media
    ".mp3": ("♪", "magenta"),
    ".wav": ("♪", "magenta"),
    ".mp4": ("▶", "magenta"),
    ".mkv": ("▶", "magenta"),
    # Archives
    ".zip": ("◇", "yellow"),
    ".tar": ("◇", "yellow"),
    ".gz": ("◇", "yellow"),
    # Security
    ".pem": ("◆", "red"),
    ".crt": ("◆", "red"),
    ".key": ("◆", "red"),
    # Lock/ignore
    ".lock": ("◆", "dim"),
    ".gitignore": ("◆", "dim"),
    # Docker
    "dockerfile": ("◎", "cyan"),
    # Nim
    ".nim": ("◇", "yellow"),
    # Executable
    ".exe": ("◎", "green"),
    ".app": ("◎", "green"),
}


def get_file_icon(path: Path) -> Tuple[str, str]:
    """Get the icon and color for a file based on its type."""
    if path.is_symlink():
        return FILE_ICONS["symlink"]

    if path.is_dir():
        return FILE_ICONS["folder"]

    # Check full filename first (for files like Dockerfile, Makefile)
    name_lower = path.name.lower()
    if name_lower in FILE_ICONS:
        return FILE_ICONS[name_lower]

    # Then check extension
    suffix = path.suffix.lower()
    if suffix in FILE_ICONS:
        return FILE_ICONS[suffix]

    return FILE_ICONS["file"]


# ═══════════════════════════════════════════════════════════════════════════════
# File Browser Widget
# ═══════════════════════════════════════════════════════════════════════════════


class FileBrowser(Widget):
    """A complete file browser widget with tree view and file operations."""

    DEFAULT_CSS = """
    FileBrowser {
        width: 1fr;
        height: 100%;
        background: $surface;
        border: solid $primary;
    }

    FileBrowser > Vertical {
        width: 100%;
        height: 100%;
    }

    FileBrowser .browser-header {
        width: 100%;
        height: 3;
        background: $surface;
        border-bottom: solid $primary;
        padding: 0 1;
    }

    FileBrowser .path-display {
        width: 1fr;
        height: 1;
        color: $accent;
    }

    FileBrowser .nav-buttons {
        width: auto;
        height: 3;
    }

    FileBrowser .nav-buttons Button {
        width: 4;
        min-width: 4;
        height: 1;
        margin: 0;
        padding: 0;
    }

    FileBrowser Tree {
        width: 100%;
        height: 1fr;
        scrollbar-size: 1 1;
    }

    FileBrowser .browser-footer {
        width: 100%;
        height: 2;
        background: $surface;
        border-top: solid $primary;
        padding: 0 1;
    }

    FileBrowser .selection-info {
        width: 1fr;
        height: 1;
        color: $muted;
    }
    """

    BINDINGS: ClassVar[list] = [
        Binding("enter", "open_selected", "Abrir"),
        Binding("backspace", "go_up", "Subir"),
        Binding("n", "new_file", "Novo Arquivo"),
        Binding("N", "new_folder", "Nova Pasta"),
        Binding("r", "rename", "Renomear"),
        Binding("delete", "delete", "Excluir"),
        Binding("c", "copy", "Copiar"),
        Binding("x", "cut", "Recortar"),
        Binding("v", "paste", "Colar"),
        Binding("space", "toggle_select", "Selecionar"),
        Binding("h", "toggle_hidden", "Mostrar Ocultos"),
        Binding("f5", "refresh", "Atualizar"),
        Binding(".", "show_context_menu", "Menu de Contexto"),
        Binding("e", "open_in_editor", "Abrir no Editor"),
        Binding("p", "open_in_paint", "Abrir no Paint"),
    ]

    class FileSelected(Message):
        """Posted when a file is selected for opening."""

        def __init__(self, file_path: Path) -> None:
            super().__init__()
            self.file_path = file_path

    class DirectoryChanged(Message):
        """Posted when the current directory changes."""

        def __init__(self, dir_path: Path) -> None:
            super().__init__()
            self.dir_path = dir_path

    class OpenInEditor(Message):
        """Postado quando um arquivo deve ser aberto no editor externo."""

        def __init__(self, file_path: Path) -> None:
            super().__init__()
            self.file_path = file_path

    class OpenInOtherPane(Message):
        """Posted when a path should be opened in the other pane."""

        def __init__(self, path: Path) -> None:
            super().__init__()
            self.path = path

    # Reference to OpenInPaint message for handler compatibility
    OpenInPaint = OpenInPaint

    # Reactive properties
    current_path: reactive[Path] = reactive(Path.cwd)
    show_hidden: reactive[bool] = reactive(False)

    def __init__(
        self,
        root_path: Optional[Path] = None,
        show_hidden: bool = False,
        pane_id: str = "left",
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._root_path = root_path or Path.cwd()
        self.current_path = self._root_path
        self.show_hidden = show_hidden
        self.pane_id = pane_id

        # Clipboard for copy/cut operations
        self._clipboard: Optional[Path] = None
        self._clipboard_operation: Optional[str] = None  # "copy" or "cut"

        # Multi-selection support
        self._selected_paths: Set[Path] = set()

        # Ignored patterns
        self._ignored_patterns: Set[str] = {
            ".git",
            "__pycache__",
            ".pytest_cache",
            "node_modules",
            ".venv",
            "venv",
            ".env",
            ".DS_Store",
            ".idea",
            ".vscode",
            ".mypy_cache",
            ".tox",
            ".eggs",
            "*.egg-info",
            "dist",
            "build",
        }

        # History for navigation
        self._history: List[Path] = []
        self._history_index: int = -1

    def compose(self) -> ComposeResult:
        with Vertical():
            # Header with path and navigation
            with Horizontal(classes="browser-header"):
                yield Static(
                    str(self.current_path), classes="path-display", id="path-display"
                )
                with Horizontal(classes="nav-buttons"):
                    yield Button("↑", id="btn-up", variant="default")
                    yield Button("⟳", id="btn-refresh", variant="default")

            # File tree
            tree: Tree[Path] = Tree(str(self.current_path), id="file-tree")
            tree.show_root = True
            tree.guide_depth = 2
            yield tree

            # Footer with selection info
            with Horizontal(classes="browser-footer"):
                yield Static("", classes="selection-info", id="selection-info")

    def on_mount(self) -> None:
        """Build the file tree when widget is mounted."""
        self._build_tree()
        # Add initial path to history
        self._add_to_history(self.current_path)

    def watch_current_path(self, new_path: Path) -> None:
        """React to current path changes."""
        self._build_tree()
        self.post_message(self.DirectoryChanged(new_path))

    def watch_show_hidden(self, show: bool) -> None:
        """React to show_hidden changes."""
        self._build_tree()

    def _build_tree(self) -> None:
        """Build the file tree from current path."""
        tree = self.query_one("#file-tree", Tree)
        tree.clear()
        tree.root.label = str(self.current_path)
        tree.root.data = self.current_path

        # Update path display
        path_display = self.query_one("#path-display", Static)
        path_display.update(str(self.current_path))

        try:
            self._add_directory_contents(tree.root, self.current_path)
            tree.root.expand()
        except PermissionError:
            self.notify(f"Permissão negada: {self.current_path}", severity="error")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def _add_directory_contents(
        self,
        parent_node: TreeNode,
        directory: Path,
    ) -> None:
        """Add directory contents to tree node."""
        try:
            items = sorted(
                directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )

            for item in items:
                # Skip hidden files if not showing them
                if not self.show_hidden and item.name.startswith("."):
                    continue

                # Skip ignored patterns
                if item.name in self._ignored_patterns:
                    continue

                icon, _color = get_file_icon(item)
                label_text = f"{icon} {item.name}"

                if item.is_dir():
                    node = parent_node.add(label_text, data=item, allow_expand=True)
                    node.add("⋯", data=None)
                else:
                    parent_node.add_leaf(label_text, data=item)

        except PermissionError:
            parent_node.add_leaf("◆ Permissão negada", data=None)
        except Exception as e:
            parent_node.add_leaf(f"✖ Error: {e}", data=None)

    def _load_directory_lazy(self, node: TreeNode) -> None:
        """Load directory contents lazily when expanded."""
        path = node.data
        if not path or not path.is_dir():
            return

        # Remove placeholder children
        while node.children:
            node.children[0].remove()

        # Add actual contents
        self._add_directory_contents(node, path)

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle node expansion for lazy loading."""
        event.stop()
        node = event.node

        # Check if this is a directory that needs loading
        if (
            node.data
            and isinstance(node.data, Path)
            and node.data.is_dir()
            and len(node.children) == 1
            and node.children[0].data is None
        ):
            self._load_directory_lazy(node)

    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle node selection."""
        event.stop()
        node = event.node
        path = node.data

        if not path or not isinstance(path, Path):
            return

        # Update selection info
        self._update_selection_info(path)

    def _update_selection_info(self, path: Path) -> None:
        """Update the selection info in footer."""
        info = self.query_one("#selection-info", Static)

        if path.is_dir():
            try:
                count = sum(1 for _ in path.iterdir())
                info.update(f"▷ {path.name} ({count} items)")
            except PermissionError:
                info.update(f"▷ {path.name} (access denied)")
        else:
            try:
                size = format_file_size(path.stat().st_size)
                modified = datetime.fromtimestamp(path.stat().st_mtime)
                info.update(
                    f"◇ {path.name} | {size} | {modified.strftime('%Y-%m-%d %H:%M')}"
                )
            except Exception:
                info.update(f"◇ {path.name}")

    def _get_selected_path(self) -> Optional[Path]:
        """Get the currently selected path."""
        tree = self.query_one("#file-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            return tree.cursor_node.data
        return self.current_path

    def _add_to_history(self, path: Path) -> None:
        """Add path to navigation history."""
        self._history, self._history_index = append_navigation_path(
            self._history, self._history_index, path
        )

    # ═══════════════════════════════════════════════════════════════════════════
    # Actions
    # ═══════════════════════════════════════════════════════════════════════════

    def action_open_selected(self) -> None:
        """Open the selected file or directory."""
        path = self._get_selected_path()
        if not path:
            return

        if path.is_dir():
            self._add_to_history(path)
            self.current_path = path
        elif path.is_file():
            self.post_message(self.FileSelected(path))

    def action_go_up(self) -> None:
        """Go to parent directory."""
        parent = self.current_path.parent
        if parent != self.current_path:
            self._add_to_history(parent)
            self.current_path = parent

    def action_new_file(self) -> None:
        """Create a new file."""
        path = self._get_selected_path()
        parent = path if path and path.is_dir() else self.current_path
        dialog = NewFileDialog(parent_path=parent, is_directory=False)
        self.mount(dialog)
        dialog.styles.align = ("center", "middle")

    def action_new_folder(self) -> None:
        """Create a new folder."""
        path = self._get_selected_path()
        parent = path if path and path.is_dir() else self.current_path
        dialog = NewFileDialog(parent_path=parent, is_directory=True)
        self.mount(dialog)
        dialog.styles.align = ("center", "middle")

    def action_rename(self) -> None:
        """Rename the selected file/folder."""
        path = self._get_selected_path()
        if path and path != self.current_path:
            dialog = RenameDialog(file_path=path)
            self.mount(dialog)
            self.call_later(self._center_dialog, dialog)

    def _center_dialog(self, dialog) -> None:
        """Center a dialog widget in the viewport."""
        dialog.styles.align_horizontal = "center"
        dialog.styles.align_vertical = "middle"

    async def action_delete(self) -> None:
        """Delete the selected file/folder."""
        path = self._get_selected_path()
        if path and path != self.current_path:
            result = await self.app.push_screen(
                SharedConfirmDialog(
                    title="Excluir",
                    message=f"Tem certeza que deseja excluir '{path.name}'?\nEsta ação não pode ser desfeita.",
                    confirm_label="Excluir",
                    cancel_label="Cancelar",
                    dangerous=True,
                ),
                wait_for_dismiss=True,
            )

            if result:
                try:
                    delete_path(path)
                    self.notify(f"Excluído: {path.name}")
                    self._build_tree()
                except PermissionError:
                    self.notify("Permissão negada", severity="error")
                except Exception as e:
                    self.notify(f"Error: {e}", severity="error")

    def action_copy(self) -> None:
        """Copy the selected file/folder to clipboard."""
        path = self._get_selected_path()
        if path:
            self._clipboard = path
            self._clipboard_operation = "copy"
            self.notify(f"Copiado: {path.name}")

    def action_cut(self) -> None:
        """Cut the selected file/folder to clipboard."""
        path = self._get_selected_path()
        if path:
            self._clipboard = path
            self._clipboard_operation = "cut"
            self.notify(f"Recortado: {path.name}")

    def action_paste(self) -> None:
        """Paste from clipboard."""
        if not self._clipboard:
            self.notify("Área de transferência vazia", severity="warning")
            return

        dest_dir = self._get_selected_path()
        if dest_dir and not dest_dir.is_dir():
            dest_dir = dest_dir.parent
        dest_dir = dest_dir or self.current_path

        self._do_paste(dest_dir)

    def _do_paste(self, dest_dir: Path) -> None:
        """Perform paste operation."""
        if not self._clipboard or not self._clipboard.exists():
            self.notify("Origem não existe mais", severity="error")
            return

        src = self._clipboard
        dest = plan_transfer_destination(src, dest_dir, exists=Path.exists)

        try:
            if self._clipboard_operation == "copy":
                transfer_path(src, dest, operation="copy")
                self.notify(f"Copiado para: {dest.name}")
            elif self._clipboard_operation == "cut":
                transfer_path(src, dest, operation="cut")
                self._clipboard = None
                self._clipboard_operation = None
                self.notify(f"Movido para: {dest.name}")

            self._build_tree()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def action_toggle_hidden(self) -> None:
        """Toggle showing hidden files."""
        self.show_hidden = not self.show_hidden
        self.notify(
            f"Arquivos ocultos: {'visíveis' if self.show_hidden else 'ocultos'}"
        )

    def action_refresh(self) -> None:
        """Refresh the current directory."""
        self._build_tree()
        self.notify("Atualizado")

    def action_show_context_menu(self) -> None:
        """Show context menu for selected item."""
        path = self._get_selected_path()
        if path:
            menu = FileContextMenu(file_path=path, is_directory=path.is_dir())
            self.mount(menu)
            menu.styles.align = ("center", "middle")

    def action_open_in_editor(self) -> None:
        """Abrir o arquivo selecionado no editor externo."""
        path = self._get_selected_path()
        if path and path.is_file():
            self.post_message(self.OpenInEditor(path))

    def action_open_in_paint(self) -> None:
        """Open the selected file in AuraPaint."""
        path = self._get_selected_path()
        if path and path.is_file():
            if is_paint_compatible(str(path)):
                self.post_message(OpenInPaint(path))
            else:
                self.notify(
                    f"Tipo de arquivo não suportado pelo Paint: {path.suffix}",
                    severity="warning",
                )

    def action_toggle_select(self) -> None:
        """Toggle selection of current item."""
        path = self._get_selected_path()
        if path:
            if path in self._selected_paths:
                self._selected_paths.discard(path)
            else:
                self._selected_paths.add(path)
            self.notify(f"Selected: {len(self._selected_paths)} items")

    # ═══════════════════════════════════════════════════════════════════════════
    # Event Handlers
    # ═══════════════════════════════════════════════════════════════════════════

    @on(Button.Pressed, "#btn-up")
    def on_up_pressed(self, event: Button.Pressed) -> None:
        self.action_go_up()

    @on(Button.Pressed, "#btn-refresh")
    def on_refresh_pressed(self, event: Button.Pressed) -> None:
        self.action_refresh()

    @on(NewFileDialog.Created)
    def on_file_created(self, event: NewFileDialog.Created) -> None:
        """Handle new file/folder creation."""
        try:
            create_path(event.path, directory=event.is_directory)
            if event.is_directory:
                self.notify(f"Pasta criada: {event.path.name}")
            else:
                self.notify(f"File created: {event.path.name}")
                # Open the new file
                self.post_message(self.FileSelected(event.path))
            self._build_tree()
        except PermissionError:
            self.notify("Permissão negada", severity="error")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    @on(RenameDialog.Renamed)
    def on_file_renamed(self, event: RenameDialog.Renamed) -> None:
        """Handle file/folder rename."""
        try:
            if event.new_path.exists():
                self.notify(f"Já existe: {event.new_path.name}", severity="error")
                return
            rename_path(event.old_path, event.new_path)
            self.notify(f"Renomeado para: {event.new_path.name}")
            self._build_tree()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def _handle_new_item(self, path: Path, is_directory: bool) -> None:
        parent = path if path.is_dir() else path.parent
        dialog = NewFileDialog(parent_path=parent, is_directory=is_directory)
        self.mount(dialog)
        dialog.styles.align = ("center", "middle")

    def _handle_clipboard_action(self, path: Path, operation: str) -> None:
        self._clipboard = path
        self._clipboard_operation = operation
        self.notify(f"{'Copiado' if operation == 'copy' else 'Recortado'}: {path.name}")

    def _handle_open_action(self, path: Path) -> None:
        if path.is_dir():
            self._add_to_history(path)
            self.current_path = path
        else:
            self.post_message(self.FileSelected(path))

    def _handle_rename_or_props(self, dialog_cls: type, path: Path) -> None:
        dialog = dialog_cls(file_path=path)
        self.mount(dialog)
        dialog.styles.align = ("center", "middle")

    def _do_delete_confirmed(self, path: Path) -> None:
        try:
            delete_path(path)
            self.notify(f"Excluído: {path.name}")
            self._build_tree()
        except PermissionError:
            self.notify("Permissão negada", severity="error")
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    async def _handle_delete_action(self, path: Path) -> None:
        result = await self.app.push_screen(
            SharedConfirmDialog(
                title="Excluir",
                message=f"Tem certeza que deseja excluir '{path.name}'?\nEsta ação não pode ser desfeita.",
                confirm_label="Excluir",
                cancel_label="Cancelar",
                dangerous=True,
            ),
            wait_for_dismiss=True,
        )
        if result:
            self._do_delete_confirmed(path)

    @on(FileContextMenu.ActionSelected)
    async def on_context_action(self, event: FileContextMenu.ActionSelected) -> None:
        """Handle context menu action."""
        action = event.action
        path = event.path

        _SIMPLE = {
            "open_with_editor": lambda: self.post_message(self.OpenInEditor(path)),
            "open_with_paint": lambda: self.post_message(OpenInPaint(path)),
            "open_in_new_pane": lambda: self.post_message(self.OpenInOtherPane(path)),
            "new_file": lambda: self._handle_new_item(path, is_directory=False),
            "new_folder": lambda: self._handle_new_item(path, is_directory=True),
            "paste": lambda: self._do_paste(path if path.is_dir() else path.parent),
            "rename": lambda: self._handle_rename_or_props(RenameDialog, path),
            "duplicate": lambda: self._duplicate_file(path),
            "copy_path": lambda: self._copy_to_clipboard(str(path)),
            "copy_name": lambda: self._copy_to_clipboard(path.name),
            "reveal": lambda: self._reveal_in_finder(path),
            "open_terminal": lambda: self._open_terminal(path),
            "properties": lambda: self._handle_rename_or_props(PropertiesDialog, path),
        }

        if action == "open":
            self._handle_open_action(path)
        elif action in ("copy", "cut"):
            self._handle_clipboard_action(path, action)
        elif action == "delete":
            await self._handle_delete_action(path)
        elif action in _SIMPLE:
            _SIMPLE[action]()

    def _duplicate_file(self, path: Path) -> None:
        """Duplicate a file."""
        try:
            if path.is_file():
                new_path = plan_duplicate_destination(path, exists=Path.exists)
                duplicate_file(path, new_path)
                self.notify(f"Duplicado: {new_path.name}")
                self._build_tree()
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def _copy_to_clipboard(self, text: str) -> bool:
        """Copy text to system clipboard and report the actual result."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["pbcopy"], input=text.encode(), check=True)
            elif sys.platform == "linux":
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(),
                    check=True,
                )
            elif sys.platform == "win32":
                subprocess.run(["clip"], input=text.encode(), check=True)
            else:
                self.notify(
                    "Área de transferência não suportada neste sistema.",
                    severity="error",
                )
                return False
            self.notify("Conteúdo copiado para a área de transferência.")
            return True
        except Exception as error:
            self.notify(
                f"Não foi possível copiar para a área de transferência: {error}",
                severity="error",
            )
            return False

    def _reveal_in_finder(self, path: Path) -> None:
        """Reveal file in system file manager."""
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", "-R", str(path)])
            elif sys.platform == "linux":
                subprocess.run(["xdg-open", str(path.parent)])
            elif sys.platform == "win32":
                subprocess.run(["explorer", "/select,", str(path)])
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def _open_terminal(self, path: Path) -> None:
        """Open terminal at directory."""
        directory = path if path.is_dir() else path.parent
        try:
            if sys.platform == "darwin":
                subprocess.Popen(["open", "-a", "Terminal", str(directory)])
            elif sys.platform == "linux":
                for term in ["gnome-terminal", "konsole", "xfce4-terminal", "xterm"]:
                    if shutil.which(term):
                        subprocess.Popen([term], cwd=str(directory))
                        break
            elif sys.platform == "win32":
                subprocess.Popen(["cmd", "/c", "start", "cmd"], cwd=str(directory))
        except Exception as e:
            self.notify(f"Error: {e}", severity="error")

    def navigate_to(self, path: Path) -> None:
        """Navigate to a specific path."""
        if path.is_dir():
            self._add_to_history(path)
            self.current_path = path
        elif path.is_file():
            self._add_to_history(path.parent)
            self.current_path = path.parent
