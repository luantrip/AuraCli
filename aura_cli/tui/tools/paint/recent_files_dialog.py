"""Recent Files Dialog for Paint Tool.

Dialog window for selecting from recently opened files.
"""

import os
from typing import Any, Callable

from textual.containers import Container, Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Button, Label, ListItem, ListView

from aura_cli.application.paint.localization.i18n import get as _

from .recent_files import load_recent_files
from .windows import DialogWindow


class RecentFilesDialogWindow(DialogWindow):
    """Dialog window for selecting a recently opened file."""

    def __init__(
        self,
        *children: Widget,
        handle_selected_file_path: Callable[[str], None],
        **kwargs: Any,
    ) -> None:
        """Initialize the recent files dialog.

        Args:
            *children: Child widgets
            handle_selected_file_path: Callback for file selection
            **kwargs: Additional dialog arguments
        """
        super().__init__(*children, handle_button=self.handle_button, **kwargs)
        self.handle_selected_file_path = handle_selected_file_path
        self.recent_files = load_recent_files()
        self.selected_file: str | None = None

    def compose(self) -> Any:
        """Compose the dialog content."""
        with Container(classes="dialog_content"):
            yield Label(_("Recent Files"), classes="dialog_title")
            with Vertical():
                if self.recent_files:
                    list_view = ListView(id="recent_files_list")
                    for file_path in self.recent_files:
                        file_name = os.path.basename(file_path)
                        list_view.append(
                            ListItem(
                                Label(f"{file_name}\n{file_path}", classes="file_path")
                            )
                        )
                    yield list_view
                else:
                    yield Label(_("No recent files."), classes="empty_message")
                with Horizontal(classes="dialog_buttons"):
                    yield Button(_("Open"), id="open_button", classes="submit")
                    yield Button(_("Cancel"), id="cancel_button", classes="cancel")

    def on_mount(self) -> None:
        """Initialize dialog on mount."""
        if self.recent_files:
            list_view = self.query_one("#recent_files_list", ListView)
            if list_view.children:
                list_view.index = 0

    def on_list_view_selected(self, event: Any) -> None:
        """Handle list item selection.

        Args:
            event: Selection event
        """
        if event.item:
            label = event.item.query_one(Label)
            text = str(label.renderable)
            lines = text.split("\n")
            if len(lines) >= 2:
                self.selected_file = lines[1]

    def handle_button(self, button: Button) -> None:
        """Handle button press events.

        Args:
            button: Button that was pressed
        """
        if button.has_class("cancel"):
            self.request_close()
        elif button.has_class("submit"):
            if self.selected_file and self.selected_file in self.recent_files:
                self.handle_selected_file_path(self.selected_file)
                self.request_close()
            else:
                list_view = self.query_one(
                    "#recent_files_list", ListView, can_ignore=True
                )
                if list_view and list_view.highlighted_child:
                    label = list_view.highlighted_child.query_one(Label)
                    text = str(label.renderable)
                    lines = text.split("\n")
                    if len(lines) >= 2:
                        file_path = lines[1]
                        if file_path in self.recent_files:
                            self.handle_selected_file_path(file_path)
                            self.request_close()
