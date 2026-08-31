"""
Select Dialog for Aura TUI.

A dialog for selecting from a list of options.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from aura_cli.tui.widgets.dialogs.base_dialog import BaseDialog, DialogResult


@dataclass
class SelectOption:
    """An option in the select dialog."""

    id: str
    label: str
    description: str = ""
    icon: str = ""
    data: Any = None

    @property
    def display(self) -> str:
        """Display the dialog and return the selected value."""
        icon = f"{self.icon} " if self.icon else ""
        return f"{icon}{self.label}"


class SelectDialog(BaseDialog):
    """
    Selection dialog for choosing from options.

    Example:
        ```python
        dialog = SelectDialog(
            title="Select Model",
            prompt="Choose an LLM model:",
            options=[
                SelectOption("gpt4", "GPT-4", "Most capable", "◉"),
                SelectOption("claude", "Claude 3", "Best for code", "◈"),
            ],
        )
        app.mount(dialog)
        ```
    """

    def __init__(
        self,
        title: str,
        options: List[SelectOption],
        prompt: str = "",
        on_select: Optional[Callable[[SelectOption], None]] = None,
        multi_select: bool = False,
        **kwargs,
    ):
        """
        Initialize the select dialog.

        Args:
            title: Dialog title
            options: List of options
            prompt: Optional prompt text
            on_select: Callback when option selected
            multi_select: Allow multiple selection
        """
        super().__init__(title=title, **kwargs)
        self.prompt = prompt
        self.options = options
        self._on_select = on_select
        self.multi_select = multi_select
        self._selected: List[SelectOption] = []

    def get_content(self) -> List:
        """Return the dialog content widget."""
        content: list[Any] = []

        if self.prompt:
            content.append(Static(self.prompt, classes="select-prompt"))

        option_list = OptionList(id="select_options")
        for opt in self.options:
            # Use plain string - styling via CSS classes
            text = opt.display
            if opt.description:
                text += f"  {opt.description}"
            option_list.add_option(Option(text, id=opt.id))

        content.append(option_list)
        return content

    def get_actions(self) -> List[tuple]:
        """Return the list of dialog action buttons."""
        if self.multi_select:
            return [
                ("Concluir", "done", "primary"),
                ("Cancelar", "cancel", "default"),
            ]
        return [
            ("Cancel", "cancel", "default"),
        ]

    def on_mount(self) -> None:
        """Focus option list on mount."""
        self.query_one("#select_options", OptionList).focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle option selection."""
        if event.option_list.id == "select_options" and event.option_id:
            selected = next((o for o in self.options if o.id == event.option_id), None)
            if selected:
                if self.multi_select:
                    if selected in self._selected:
                        self._selected.remove(selected)
                    else:
                        self._selected.append(selected)
                else:
                    # Single select - close immediately
                    if self._on_select:
                        self._on_select(selected)
                    self.close(DialogResult(True, value=selected, action="select"))

    def on_action(self, action: str) -> None:
        """Handle a dialog action button press."""
        if action == "done":
            self.close(DialogResult(True, value=self._selected, action="done"))
        else:
            self.close(DialogResult(False, action="cancel"))
