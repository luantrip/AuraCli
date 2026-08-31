"""Dialogs and context menu for the Textual file manager."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, List, Tuple

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Button, Input, ListItem, ListView, Static

from aura_cli.application.presentation.file_browser import (
    format_file_permissions,
    format_file_size,
    resolve_child_path,
)
from aura_cli.tui.tools.integrations import is_paint_compatible

# ═══════════════════════════════════════════════════════════════════════════════
# Context Menu
# ═══════════════════════════════════════════════════════════════════════════════


class FileContextMenu(Widget):
    """Context menu for file operations."""

    DEFAULT_CSS = """
    FileContextMenu {
        layer: overlay;
        width: 30;
        height: auto;
        max-height: 20;
        background: $surface;
        border: solid $primary;
        padding: 0;
    }

    FileContextMenu ListView {
        width: 100%;
        height: auto;
        background: $surface;
    }

    FileContextMenu ListItem {
        padding: 0 1;
        height: 1;
    }

    FileContextMenu ListItem:hover {
        background: $primary 30%;
    }

    FileContextMenu .separator {
        height: 1;
        background: $primary 30%;
        margin: 0 1;
    }
    """

    BINDINGS: ClassVar[list] = [
        Binding("escape", "dismiss", "Fechar"),
        Binding("enter", "select", "Select"),
        Binding("up", "cursor_up", "Up"),
        Binding("down", "cursor_down", "Down"),
    ]

    class ActionSelected(Message):
        """Posted when a menu action is selected."""

        def __init__(self, action: str, path: Path):
            super().__init__()
            self.action = action
            self.path = path

    def __init__(self, file_path: Path, is_directory: bool = False, **kwargs: Any):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.is_directory = is_directory
        self._actions: List[Tuple[str, str, str]] = []
        self._setup_actions()

    def _setup_actions(self) -> None:
        """Set up menu actions based on file type."""
        if self.is_directory:
            self._actions = [
                ("open", "◇ Abrir", ""),
                ("open_in_new_pane", "◫ Abrir no Outro Painel", ""),
                ("separator", "", ""),
                ("new_file", "◇ Novo Arquivo", "n"),
                ("new_folder", "▷ Nova Pasta", "N"),
                ("separator", "", ""),
                ("copy", "⊞ Copiar", "c"),
                ("cut", "⊟ Recortar", "x"),
                ("paste", "↓ Colar", "v"),
                ("separator", "", ""),
                ("rename", "✎ Renomear", "r"),
                ("delete", "✖ Excluir", "Del"),
                ("separator", "", ""),
                ("copy_path", "⊞ Copiar Caminho", ""),
                ("open_terminal", "▶ Abrir Terminal Aqui", ""),
                ("properties", "◎ Propriedades", ""),
            ]
        else:
            # Check if file is paint-compatible
            is_paintable = is_paint_compatible(str(self.file_path))

            self._actions = [
                ("open", "◇ Abrir", "Enter"),
                ("open_with_editor", "✎ Abrir no Editor", "e"),
            ]

            # Add Paint option for compatible files
            if is_paintable:
                self._actions.append(("open_with_paint", "◐ Abrir no Paint", "p"))

            self._actions.extend(
                [
                    ("open_in_new_pane", "◫ Abrir no Outro Painel", ""),
                    ("separator", "", ""),
                    ("copy", "⊞ Copiar", "c"),
                    ("cut", "⊟ Recortar", "x"),
                    ("separator", "", ""),
                    ("rename", "✎ Renomear", "r"),
                    ("duplicate", "⊞ Duplicar", "d"),
                    ("delete", "✖ Excluir", "Del"),
                    ("separator", "", ""),
                    ("copy_path", "⊞ Copiar Caminho", ""),
                    ("copy_name", "⊞ Copiar Nome", ""),
                    ("reveal", "◎ Revelar no Finder", ""),
                    ("properties", "◎ Propriedades", ""),
                ]
            )

    def compose(self) -> ComposeResult:
        with ListView(id="menu-list"):
            for action_id, label, shortcut in self._actions:
                if action_id == "separator":
                    yield ListItem(Static("", classes="separator"), disabled=True)
                else:
                    text = f"{label}"
                    if shortcut:
                        text = f"{label:<20} {shortcut:>5}"
                    item = ListItem(Static(text))
                    item.action_id = action_id
                    yield item

    def on_mount(self) -> None:
        """Focus the list when mounted."""
        self.query_one("#menu-list", ListView).focus()

    @on(ListView.Selected, "#menu-list")
    def on_menu_selected(self, event: ListView.Selected) -> None:
        """Handle menu item selection."""
        if hasattr(event.item, "action_id"):
            action_id = event.item.action_id
            if action_id != "separator":
                self.post_message(self.ActionSelected(action_id, self.file_path))
                self.remove()

    def action_dismiss(self) -> None:
        """Close the menu."""
        self.remove()

    def action_select(self) -> None:
        """Select current item."""
        list_view = self.query_one("#menu-list", ListView)
        if list_view.highlighted_child and hasattr(
            list_view.highlighted_child, "action_id"
        ):
            action_id = list_view.highlighted_child.action_id
            if action_id != "separator":
                self.post_message(self.ActionSelected(action_id, self.file_path))
                self.remove()


# ═══════════════════════════════════════════════════════════════════════════════
# Dialogs
# ═══════════════════════════════════════════════════════════════════════════════


class RenameDialog(Widget):
    """Dialog for renaming files/folders."""

    DEFAULT_CSS = """
    RenameDialog {
        layer: overlay;
        width: 60;
        height: 9;
        background: $surface;
        border: double $primary;
        border-title-color: $accent;
    }

    RenameDialog > Vertical {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    RenameDialog Input {
        width: 100%;
        margin-bottom: 1;
    }

    RenameDialog .button-bar {
        width: 100%;
        height: 3;
        align: center middle;
    }

    RenameDialog Button {
        width: auto;
        min-width: 12;
        margin: 0 1;
    }
    """

    class Renamed(Message):
        """Posted when rename is confirmed."""

        def __init__(self, old_path: Path, new_path: Path):
            super().__init__()
            self.old_path = old_path
            self.new_path = new_path

    BINDINGS: ClassVar[list] = [
        Binding("escape", "cancel", "Cancelar"),
    ]

    def __init__(self, file_path: Path, **kwargs: Any):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.border_title = f"Rename: {file_path.name}"

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static("Novo nome:")
            yield Input(value=self.file_path.name, id="rename-input")
            with Horizontal(classes="button-bar"):
                yield Button("Renomear", id="btn-rename", variant="primary")
                yield Button("Cancelar", id="btn-cancel")

    def on_mount(self) -> None:
        """Focus input and select text."""
        input_widget = self.query_one("#rename-input", Input)
        input_widget.focus()
        # Position cursor at end of name without extension
        name = self.file_path.stem
        input_widget.cursor_position = len(name)

    @on(Button.Pressed, "#btn-rename")
    def on_rename_pressed(self, event: Button.Pressed) -> None:
        self._do_rename()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_pressed(self, event: Button.Pressed) -> None:
        self.remove()

    @on(Input.Submitted, "#rename-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_rename()

    def _do_rename(self) -> None:
        """Perform the rename."""
        new_name = self.query_one("#rename-input", Input).value.strip()
        if new_name and new_name != self.file_path.name:
            try:
                new_path = resolve_child_path(self.file_path.parent, new_name)
            except ValueError as error:
                self.notify(str(error), severity="error")
                return
            self.post_message(self.Renamed(self.file_path, new_path))
        self.remove()

    def action_cancel(self) -> None:
        self.remove()


class NewFileDialog(Widget):
    """Dialog for creating new files/folders."""

    DEFAULT_CSS = """
    NewFileDialog {
        layer: overlay;
        width: 60;
        height: 9;
        background: $surface;
        border: double $primary;
        border-title-color: $accent;
    }

    NewFileDialog > Vertical {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    NewFileDialog Input {
        width: 100%;
        margin-bottom: 1;
    }

    NewFileDialog .button-bar {
        width: 100%;
        height: 3;
        align: center middle;
    }

    NewFileDialog Button {
        width: auto;
        min-width: 12;
        margin: 0 1;
    }
    """

    class Created(Message):
        """Posted when file/folder is created."""

        def __init__(self, path: Path, is_directory: bool):
            super().__init__()
            self.path = path
            self.is_directory = is_directory

    BINDINGS: ClassVar[list] = [
        Binding("escape", "cancel", "Cancelar"),
    ]

    def __init__(self, parent_path: Path, is_directory: bool = False, **kwargs: Any):
        super().__init__(**kwargs)
        self.parent_path = parent_path
        self.is_directory = is_directory
        self.border_title = "Nova Pasta" if is_directory else "Novo Arquivo"

    def compose(self) -> ComposeResult:
        with Vertical():
            placeholder = "Nome da pasta" if self.is_directory else "Nome do arquivo"
            yield Static(f"Criar em: {self.parent_path}")
            yield Input(placeholder=placeholder, id="new-name-input")
            with Horizontal(classes="button-bar"):
                yield Button("Criar", id="btn-create", variant="primary")
                yield Button("Cancelar", id="btn-cancel")

    def on_mount(self) -> None:
        self.query_one("#new-name-input", Input).focus()

    @on(Button.Pressed, "#btn-create")
    def on_create_pressed(self, event: Button.Pressed) -> None:
        self._do_create()

    @on(Button.Pressed, "#btn-cancel")
    def on_cancel_pressed(self, event: Button.Pressed) -> None:
        self.remove()

    @on(Input.Submitted, "#new-name-input")
    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._do_create()

    def _do_create(self) -> None:
        """Create the file/folder."""
        name = self.query_one("#new-name-input", Input).value.strip()
        if name:
            try:
                new_path = resolve_child_path(self.parent_path, name)
            except ValueError as error:
                self.notify(str(error), severity="error")
                return
            self.post_message(self.Created(new_path, self.is_directory))
        self.remove()

    def action_cancel(self) -> None:
        self.remove()


class PropertiesDialog(Widget):
    """Dialog showing file/folder properties."""

    DEFAULT_CSS = """
    PropertiesDialog {
        layer: overlay;
        width: 70;
        height: 18;
        background: $surface;
        border: double $primary;
        border-title-color: $accent;
    }

    PropertiesDialog > Vertical {
        width: 100%;
        height: 100%;
        padding: 1 2;
    }

    PropertiesDialog .prop-row {
        width: 100%;
        height: 1;
        margin-bottom: 0;
    }

    PropertiesDialog .prop-label {
        width: 15;
        color: $muted;
    }

    PropertiesDialog .prop-value {
        width: 1fr;
    }

    PropertiesDialog .button-bar {
        width: 100%;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    PropertiesDialog Button {
        width: auto;
        min-width: 12;
    }
    """

    BINDINGS: ClassVar[list] = [
        Binding("escape", "close", "Fechar"),
        Binding("enter", "close", "Fechar"),
    ]

    def __init__(self, file_path: Path, **kwargs: Any):
        super().__init__(**kwargs)
        self.file_path = file_path
        self.border_title = f"Properties: {file_path.name}"

    def compose(self) -> ComposeResult:
        path = self.file_path
        icon = "▷" if path.is_dir() else "◇"

        try:
            stat_info = path.stat()
            size = stat_info.st_size
            modified = datetime.fromtimestamp(stat_info.st_mtime)
            created = datetime.fromtimestamp(stat_info.st_ctime)
            accessed = datetime.fromtimestamp(stat_info.st_atime)
            permissions = format_file_permissions(stat_info.st_mode)
        except Exception:
            size = 0
            modified = created = accessed = datetime.now()
            permissions = "---"

        # Calculate directory size if it's a directory
        if path.is_dir():
            try:
                total_size = sum(
                    f.stat().st_size for f in path.rglob("*") if f.is_file()
                )
                item_count = sum(1 for _ in path.iterdir())
                size_str = f"{format_file_size(total_size)} ({item_count} items)"
            except Exception:
                size_str = "Unable to calculate"
        else:
            size_str = format_file_size(size)

        with Vertical():
            # Icon and name
            with Horizontal(classes="prop-row"):
                yield Static(f"{icon} {path.name}", classes="prop-value")

            yield Static("─" * 60)

            # Type
            file_type = (
                "Folder" if path.is_dir() else f"File ({path.suffix or 'unknown'})"
            )
            with Horizontal(classes="prop-row"):
                yield Static("Type:", classes="prop-label")
                yield Static(file_type, classes="prop-value")

            # Location
            with Horizontal(classes="prop-row"):
                yield Static("Location:", classes="prop-label")
                yield Static(str(path.parent), classes="prop-value")

            # Size
            with Horizontal(classes="prop-row"):
                yield Static("Size:", classes="prop-label")
                yield Static(size_str, classes="prop-value")

            yield Static("─" * 60)

            # Modified
            with Horizontal(classes="prop-row"):
                yield Static("Modified:", classes="prop-label")
                yield Static(
                    modified.strftime("%Y-%m-%d %H:%M:%S"), classes="prop-value"
                )

            # Created
            with Horizontal(classes="prop-row"):
                yield Static("Created:", classes="prop-label")
                yield Static(
                    created.strftime("%Y-%m-%d %H:%M:%S"), classes="prop-value"
                )

            # Accessed
            with Horizontal(classes="prop-row"):
                yield Static("Accessed:", classes="prop-label")
                yield Static(
                    accessed.strftime("%Y-%m-%d %H:%M:%S"), classes="prop-value"
                )

            yield Static("─" * 60)

            # Permissions
            with Horizontal(classes="prop-row"):
                yield Static("Permissions:", classes="prop-label")
                yield Static(permissions, classes="prop-value")

            # Symlink target
            if path.is_symlink():
                try:
                    target = path.resolve()
                    with Horizontal(classes="prop-row"):
                        yield Static("Target:", classes="prop-label")
                        yield Static(str(target), classes="prop-value")
                except OSError as error:
                    yield Static(f"Target unavailable: {error}", classes="prop-value")

            with Horizontal(classes="button-bar"):
                yield Button("Fechar", id="btn-close", variant="primary")

    def on_mount(self) -> None:
        self.query_one("#btn-close", Button).focus()

    @on(Button.Pressed, "#btn-close")
    def on_close_pressed(self, event: Button.Pressed) -> None:
        self.remove()

    def action_close(self) -> None:
        self.remove()
