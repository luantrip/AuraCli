"""File Dialogs - Aura CLI Paint Tool.

Open and Save file dialog windows with directory tree navigation
and filename input.

Features:
    - Directory tree navigation
    - Filename input with validation
    - Auto-extension addition
    - Path expansion (~ and environment variables)
    - Keyboard navigation support
"""

import contextlib
import os
from typing import Any, Callable

from textual.containers import Container, Horizontal
from textual.css.query import NoMatches
from textual.widget import Widget
from textual.widgets import Button, Input, Label, Tree
from textual.widgets._directory_tree import DirEntry

from aura_cli.application.paint.localization.i18n import get as _

from .enhanced_directory_tree import EnhancedDirectoryTree
from .windows import DialogWindow


class FileDialogWindow(DialogWindow):
    """File selection dialog with directory tree.

    Provides file browser with tree navigation and filename input.
    Supports path expansion and auto-extension addition.

    Attributes:
        handle_selected_file_path: Callback for file selection
    """

    def __init__(
        self,
        *children: Widget,
        file_name: str = "",
        selected_file_path: str | None,
        handle_selected_file_path: Callable[[str], None],
        auto_add_default_extension: str = "",
        submit_label: str,
        **kwargs: Any,
    ) -> None:
        """Initialize file dialog.

        Args:
            *children: Child widgets
            file_name: Initial filename
            selected_file_path: Initially selected file path
            handle_selected_file_path: Callback for file selection
            auto_add_default_extension: Extension to add if missing
            submit_label: Label for submit button
            **kwargs: Additional dialog arguments
        """
        super().__init__(*children, handle_button=self.handle_button, **kwargs)

        self._starting_file_name: str = file_name
        self._selected_file_path: str | None = selected_file_path
        self._submit_label: str = submit_label
        self.handle_selected_file_path = handle_selected_file_path
        self._directory_tree_selected_path: str | None = None
        self._auto_add_default_extension: str = auto_add_default_extension

    def handle_button(self, button: Button) -> None:
        """Handle button press events.

        Args:
            button: Button that was pressed
        """
        if button.has_class("cancel"):
            self.request_close()
        elif button.has_class("submit"):
            filename = self.content.query_one(".filename_input", Input).value
            if not filename:
                return

            file_path = filename
            file_path = os.path.expanduser(file_path)
            file_path = os.path.expandvars(file_path)

            if self._directory_tree_selected_path:
                file_path = os.path.join(self._directory_tree_selected_path, file_path)

            if os.path.splitext(file_path)[1] == "":
                file_path += self._auto_add_default_extension

            if os.path.isdir(file_path):
                tree = self.content.query_one(EnhancedDirectoryTree)
                tree.expand_to_path(file_path)
                return

            self.handle_selected_file_path(file_path)

    def on_mount(self) -> None:
        """Initialize dialog components on mount."""
        self.content.mount(
            EnhancedDirectoryTree(path="/"),
            Horizontal(
                Label(_("File name:")),
                Input(
                    classes="filename_input autofocus", value=self._starting_file_name
                ),
            ),
            Container(
                Button(self._submit_label, classes="submit", variant="primary"),
                Button(_("Cancel"), classes="cancel"),
                classes="buttons",
            ),
        )
        self._expand_directory_tree()

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[DirEntry]) -> None:
        """
        Called when a file/folder is selected in the DirectoryTree.

        This message comes from Tree.
        ~~DirectoryTree gives FileSelected, but only for files, not folders.~~
        Update: as of Textual 0.37.0, DirectoryTree gives DirectorySelected for folders.
        TODO: does that make it cleaner, or is it still awkward because it's two different messages?
        """
        assert event.node.data

        if event.node.data.path.is_dir():
            self._directory_tree_selected_path = str(event.node.data.path)
        elif event.node.parent:
            assert event.node.parent.data
            self._directory_tree_selected_path = str(event.node.parent.data.path)
            name = os.path.basename(event.node.data.path)
            assert isinstance(event.control, EnhancedDirectoryTree)
            if not event.control.node_highlighted_by_expand_to_path:
                with contextlib.suppress(NoMatches):
                    self.query_one(
                        "FileDialogWindow .filename_input", Input
                    ).value = name
        else:
            self._directory_tree_selected_path = None

    def _expand_directory_tree(self) -> None:
        """Expand the directory tree to the target directory, either the folder of the open file or the current working directory."""
        tree = self.content.query_one(EnhancedDirectoryTree)
        target_dir = (self._selected_file_path or os.getcwd()).rstrip(os.path.sep)
        tree.expand_to_path(target_dir)


class OpenDialogWindow(FileDialogWindow):
    """A dialog window that lets the user select a file to open.

    `handle_selected_file_path` is called when the user clicks the Open button,
    and the window is NOT closed in that case.
    """

    def __init__(
        self,
        *children: Widget,
        selected_file_path: str | None,
        handle_selected_file_path: Callable[[str], None],
        **kwargs: Any,
    ) -> None:
        """Initialize the dialog window."""
        super().__init__(
            *children,
            submit_label=_("Open"),
            file_name="",
            selected_file_path=selected_file_path,
            handle_selected_file_path=handle_selected_file_path,
            **kwargs,
        )


class SaveAsDialogWindow(FileDialogWindow):
    """A dialog window that lets the user select a file to save to.

    `handle_selected_file_path` is called when the user clicks the Save button,
    and the window is NOT closed in that case.
    """

    def __init__(
        self,
        *children: Widget,
        file_name: str = "",
        selected_file_path: str | None,
        handle_selected_file_path: Callable[[str], None],
        auto_add_default_extension: str = "",
        **kwargs: Any,
    ) -> None:
        """Initialize the dialog window."""
        super().__init__(
            *children,
            submit_label=_("Save"),
            file_name=file_name,
            selected_file_path=selected_file_path,
            handle_selected_file_path=handle_selected_file_path,
            auto_add_default_extension=auto_add_default_extension,
            **kwargs,
        )
