"""File Manager main screen.

Dual-pane file manager interface similar to Midnight Commander.

Features:
    - Dual-pane navigation
    - Rich file operations
    - Code editor integration
    - Toolbar with quick actions
    - Status bar with file info
    - Keyboard shortcuts
    - File preview panel

Classes:
    FileManagerScreen: Main file manager screen with dual panes
"""

from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Optional

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Button, Header, Input, Static

from .components.file_browser import FileBrowser
from .components.status_bar import FileManagerStatusBar, FilePreview


class FileManagerScreen(Screen):
    """A full-screen dual-pane file manager interface."""

    CSS = """
    FileManagerScreen {
        background: $surface;
    }

    FileManagerScreen > Vertical {
        width: 100%;
        height: 100%;
    }

    /* Toolbar */
    .toolbar {
        width: 100%;
        height: 3;
        background: $surface;
        border-bottom: solid $primary;
        padding: 0 1;
        layout: horizontal;
    }

    .toolbar Button {
        width: auto;
        min-width: 8;
        height: 1;
        margin-right: 1;
    }

    .toolbar .spacer {
        width: 1fr;
    }

    .toolbar Input {
        width: 30;
        height: 1;
    }

    /* Main content area */
    .main-content {
        width: 100%;
        height: 1fr;
        layout: horizontal;
    }

    /* Pane containers */
    .pane-container {
        width: 1fr;
        height: 100%;
    }

    .pane-container.active {
        border: double $accent;
    }

    /* Preview panel (optional) */
    .preview-panel {
        width: 40;
        height: 100%;
        display: none;
    }

    .preview-panel.visible {
        display: block;
    }

    /* File browsers */
    FileBrowser {
        width: 100%;
        height: 100%;
    }

    /* Status bar */
    FileManagerStatusBar {
        dock: bottom;
    }

    /* Quick actions bar */
    .quick-actions {
        width: 100%;
        height: 2;
        background: $primary 20%;
        border-top: solid $primary;
        layout: horizontal;
        padding: 0 1;
    }

    .quick-actions Static {
        width: auto;
        margin-right: 2;
        color: $text;
    }

    .quick-actions .shortcut {
        color: $accent;
        text-style: bold;
    }
    """

    BINDINGS: ClassVar[list] = [
        Binding("q", "quit_screen", "Quit", show=True),
        Binding("escape", "quit_screen", "Quit", show=False),
        Binding("tab", "switch_pane", "Switch Pane", show=True),
        Binding("f1", "show_help", "Help", show=True),
        Binding("f3", "view_file", "View", show=True),
        Binding("f4", "edit_file", "Edit", show=True),
        Binding("f5", "copy_file", "Copy", show=True),
        Binding("f6", "move_file", "Move", show=True),
        Binding("f7", "new_folder", "New Folder", show=True),
        Binding("f8", "delete_file", "Delete", show=True),
        Binding("f9", "toggle_preview", "Preview", show=True),
        Binding("f10", "quit_screen", "Quit", show=True),
        Binding("ctrl+r", "refresh", "Refresh"),
        Binding("ctrl+h", "toggle_hidden", "Hidden"),
        Binding("ctrl+l", "focus_path", "Go to"),
        Binding("ctrl+o", "open_in_editor", "Open in Editor"),
    ]

    # Reactive properties
    active_pane: reactive[str] = reactive("left")
    show_preview: reactive[bool] = reactive(False)

    def __init__(
        self,
        left_path: Optional[Path] = None,
        right_path: Optional[Path] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._left_path = left_path or Path.cwd()
        self._right_path = right_path or Path.home()

        # Clipboard for cross-pane operations
        self._clipboard: Optional[Path] = None
        self._clipboard_operation: Optional[str] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)

        with Vertical():
            # Toolbar
            with Horizontal(classes="toolbar"):
                yield Button("↑ Up", id="btn-up")
                yield Button("⌂ Home", id="btn-home")
                yield Button("▷ Root", id="btn-root")
                yield Button("⟳ Refresh", id="btn-refresh")
                yield Static("", classes="spacer")
                yield Input(placeholder="Go to path...", id="path-input")

            # Main dual-pane area
            with Horizontal(classes="main-content"):
                # Left pane
                with Container(classes="pane-container active", id="left-pane"):
                    yield FileBrowser(
                        root_path=self._left_path, pane_id="left", id="browser-left"
                    )

                # Right pane
                with Container(classes="pane-container", id="right-pane"):
                    yield FileBrowser(
                        root_path=self._right_path, pane_id="right", id="browser-right"
                    )

                # Preview panel (hidden by default)
                with Container(classes="preview-panel", id="preview-panel"):
                    yield FilePreview(id="file-preview")

            # Quick actions bar (Midnight Commander style)
            with Horizontal(classes="quick-actions"):
                yield Static("F1 Help", classes="quick-action-item")
                yield Static("F3 View", classes="quick-action-item")
                yield Static("F4 Edit", classes="quick-action-item")
                yield Static("F5 Copy", classes="quick-action-item")
                yield Static("F6 Move", classes="quick-action-item")
                yield Static("F7 Folder", classes="quick-action-item")
                yield Static("F8 Delete", classes="quick-action-item")
                yield Static("F9 Preview", classes="quick-action-item")
                yield Static("F10 Quit", classes="quick-action-item")

        yield FileManagerStatusBar(id="status-bar")

    def on_mount(self) -> None:
        """Focus the left pane on mount."""
        self._focus_active_pane()

    def watch_active_pane(self, pane: str) -> None:
        """Update visual indication of active pane."""
        left_pane = self.query_one("#left-pane", Container)
        right_pane = self.query_one("#right-pane", Container)

        if pane == "left":
            left_pane.add_class("active")
            right_pane.remove_class("active")
        else:
            left_pane.remove_class("active")
            right_pane.add_class("active")

        self._focus_active_pane()

    def watch_show_preview(self, show: bool) -> None:
        """Toggle preview panel visibility."""
        preview = self.query_one("#preview-panel", Container)
        if show:
            preview.add_class("visible")
        else:
            preview.remove_class("visible")

    def _focus_active_pane(self) -> None:
        """Focus the active file browser."""
        browser_id = f"browser-{self.active_pane}"
        try:
            browser = self.query_one(f"#{browser_id}", FileBrowser)
            browser.focus()
        except Exception as error:
            self.log.debug("Active file pane is not mounted yet: %s", error)

    def _get_active_browser(self) -> FileBrowser:
        """Get the currently active file browser."""
        browser_id = f"browser-{self.active_pane}"
        return self.query_one(f"#{browser_id}", FileBrowser)

    def _get_inactive_browser(self) -> FileBrowser:
        """Get the inactive file browser."""
        other_pane = "right" if self.active_pane == "left" else "left"
        browser_id = f"browser-{other_pane}"
        return self.query_one(f"#{browser_id}", FileBrowser)

    # ═══════════════════════════════════════════════════════════════════════════
    # Actions
    # ═══════════════════════════════════════════════════════════════════════════

    def action_quit_screen(self) -> None:
        """Quit the file manager screen."""
        self.app.pop_screen()

    def action_switch_pane(self) -> None:
        """Switch between left and right panes."""
        self.active_pane = "right" if self.active_pane == "left" else "left"

    def action_show_help(self) -> None:
        """Show help dialog."""
        help_text = """
╔══════════════════════════════════════════════════════════════╗
║                   FILE MANAGER — HELP                        ║
╠══════════════════════════════════════════════════════════════╣
║  Navigation                                                   ║
║  ──────────                                                   ║
║  Tab        Switch between panes                             ║
║  Enter      Open file/folder                                 ║
║  Backspace  Go to parent directory                           ║
║  Ctrl+L     Go to specific path                              ║
║                                                               ║
║  File Operations                                             ║
║  ───────────────                                              ║
║  F3/e       View/Edit file                                   ║
║  F4         Edit file in code editor                         ║
║  F5/c       Copy file                                        ║
║  F6/x       Move (cut) file                                  ║
║  F7/N       Create new folder                                ║
║  F8/Del     Delete file/folder                               ║
║  n          Create new file                                  ║
║  r          Rename file/folder                               ║
║  v          Paste from clipboard                             ║
║                                                               ║
║  View Options                                                ║
║  ────────────                                                 ║
║  F9         Toggle preview panel                             ║
║  Ctrl+H     Toggle hidden files                              ║
║  Ctrl+R/F5  Refresh view                                     ║
║                                                               ║
║  Press Escape or F10 to close this help                      ║
╚══════════════════════════════════════════════════════════════╝
"""
        self.notify(help_text, title="Help", timeout=10)

    def action_view_file(self) -> None:
        """View the selected file."""
        browser = self._get_active_browser()
        path = browser._get_selected_path()
        if path and path.is_file():
            # Show in preview panel
            self.show_preview = True
            preview = self.query_one("#file-preview", FilePreview)
            preview.current_file = path

    def action_edit_file(self) -> None:
        """Open the selected file in the code editor."""
        browser = self._get_active_browser()
        path = browser._get_selected_path()
        if path and path.is_file():
            browser.post_message(FileBrowser.OpenInEditor(path))

    def action_copy_file(self) -> None:
        """Copy selected file for cross-pane operation."""
        browser = self._get_active_browser()
        browser.action_copy()

        # Also set screen-level clipboard for cross-pane
        path = browser._get_selected_path()
        if path:
            self._clipboard = path
            self._clipboard_operation = "copy"
            status = self.query_one("#status-bar", FileManagerStatusBar)
            status.clipboard_info = f"⊞ Copy: {path.name}"

    def action_move_file(self) -> None:
        """Cut selected file for cross-pane operation."""
        browser = self._get_active_browser()
        browser.action_cut()

        # Also set screen-level clipboard for cross-pane
        path = browser._get_selected_path()
        if path:
            self._clipboard = path
            self._clipboard_operation = "cut"
            status = self.query_one("#status-bar", FileManagerStatusBar)
            status.clipboard_info = f"⊠ Recortar: {path.name}"

    def action_new_folder(self) -> None:
        """Create a new folder."""
        browser = self._get_active_browser()
        browser.action_new_folder()

    def action_delete_file(self) -> None:
        """Delete the selected file/folder."""
        browser = self._get_active_browser()
        browser.action_delete()

    def action_toggle_preview(self) -> None:
        """Toggle the preview panel."""
        self.show_preview = not self.show_preview

        if self.show_preview:
            # Update preview with current selection
            browser = self._get_active_browser()
            path = browser._get_selected_path()
            if path:
                preview = self.query_one("#file-preview", FilePreview)
                preview.current_file = path

    def action_refresh(self) -> None:
        """Refresh both panes."""
        self.query_one("#browser-left", FileBrowser).action_refresh()
        self.query_one("#browser-right", FileBrowser).action_refresh()
        self.notify("Atualizado")

    def action_toggle_hidden(self) -> None:
        """Toggle hidden files in active pane."""
        browser = self._get_active_browser()
        browser.action_toggle_hidden()

    def action_focus_path(self) -> None:
        """Focus the path input."""
        path_input = self.query_one("#path-input", Input)
        path_input.focus()
        path_input.value = str(self._get_active_browser().current_path)

    def action_open_in_editor(self) -> None:
        """Open selected file in code editor."""
        browser = self._get_active_browser()
        browser.action_open_in_editor()

    # ═══════════════════════════════════════════════════════════════════════════
    # Event Handlers
    # ═══════════════════════════════════════════════════════════════════════════

    @on(Button.Pressed, "#btn-up")
    def on_up_pressed(self, event: Button.Pressed) -> None:
        """Go to parent directory."""
        browser = self._get_active_browser()
        browser.action_go_up()

    @on(Button.Pressed, "#btn-home")
    def on_home_pressed(self, event: Button.Pressed) -> None:
        """Go to home directory."""
        browser = self._get_active_browser()
        browser.navigate_to(Path.home())

    @on(Button.Pressed, "#btn-root")
    def on_root_pressed(self, event: Button.Pressed) -> None:
        """Go to root directory."""
        browser = self._get_active_browser()
        browser.navigate_to(Path("/"))

    @on(Button.Pressed, "#btn-refresh")
    def on_refresh_pressed(self, event: Button.Pressed) -> None:
        """Refresh current view."""
        browser = self._get_active_browser()
        browser.action_refresh()

    @on(Input.Submitted, "#path-input")
    def on_path_submitted(self, event: Input.Submitted) -> None:
        """Navigate to entered path."""
        path_str = event.value.strip()
        if not path_str:
            return

        # Expand ~ to home
        if path_str.startswith("~"):
            path_str = str(Path.home()) + path_str[1:]

        path = Path(path_str)
        if path.exists():
            browser = self._get_active_browser()
            browser.navigate_to(path)
            self._focus_active_pane()
        else:
            self.notify(f"Path not found: {path}", severity="error")

    @on(FileBrowser.FileSelected)
    def on_file_selected(self, event: FileBrowser.FileSelected) -> None:
        """Handle file selection."""
        # Update preview if visible
        if self.show_preview:
            preview = self.query_one("#file-preview", FilePreview)
            preview.current_file = event.file_path

        # Update status bar
        status = self.query_one("#status-bar", FileManagerStatusBar)
        status.selected_path = event.file_path

    @on(FileBrowser.DirectoryChanged)
    def on_directory_changed(self, event: FileBrowser.DirectoryChanged) -> None:
        """Handle directory change."""
        status = self.query_one("#status-bar", FileManagerStatusBar)
        status._update_disk_info(event.dir_path)

    @on(FileBrowser.OpenInEditor)
    def on_open_in_editor(self, event: FileBrowser.OpenInEditor) -> None:
        """Handle request to open file in editor."""
        # Post message to parent app to open in code editor
        self.app.post_message(event)

        # Also pop back to main screen
        self.notify(f"Abrindo {event.file_path.name} no editor...")

    @on(FileBrowser.OpenInPaint)
    def on_open_in_paint(self, event: FileBrowser.OpenInPaint) -> None:
        """Handle request to open a file in AuraPaint."""
        # Post message to parent app to open in paint
        self.app.post_message(event)

        self.notify(f"Abrindo {event.file_path.name} no Paint...")

    @on(FileBrowser.OpenInOtherPane)
    def on_open_in_other_pane(self, event: FileBrowser.OpenInOtherPane) -> None:
        """Handle request to open in the other pane."""
        other_browser = self._get_inactive_browser()
        other_browser.navigate_to(event.path)


# ═══════════════════════════════════════════════════════════════════════════════
# Simple File Manager App (for standalone testing)
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    from textual.app import App

    class FileManagerApp(App):
        """Standalone File Manager application."""

        TITLE = "Aura File Manager"

        def on_mount(self) -> None:
            self.push_screen(FileManagerScreen())

    app = FileManagerApp()
    app.run()
