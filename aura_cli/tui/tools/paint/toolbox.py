"""Toolbox Widget - Aura CLI Paint Tool.

Container widget for tool selection buttons with visual feedback
and tooltip support.

Features:
    - Button for each drawing tool
    - Tool icons and tooltips
    - Selected tool highlighting
    - Keyboard-accessible tool selection
"""

from typing import Dict

from textual.app import ComposeResult
from textual.containers import Container
from textual.message import Message
from textual.widgets import Button

from .tool import Tool


class ToolsBox(Container):
    """Toolbox widget with tool selection buttons.

    Displays a button for each available tool with icon and tooltip.
    Highlights currently selected tool.
    """

    class ToolSelected(Message):
        """Message posted when tool is selected.

        Attributes:
            tool: Selected tool
        """

        def __init__(self, tool: Tool) -> None:
            self.tool = tool
            super().__init__()

    def compose(self) -> ComposeResult:
        """Compose tool buttons."""
        self.tool_by_button: Dict[Button, Tool] = {}
        for tool in Tool:
            button = Button(tool.get_icon(), classes="tool_button")
            button.can_focus = False
            button.tooltip = tool.get_name()
            self.tool_by_button[button] = tool
            yield button

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle tool button press.

        Args:
            event: Button press event
        """
        if "tool_button" in event.button.classes:
            self.post_message(self.ToolSelected(self.tool_by_button[event.button]))

    def show_selected_tool(self, selected_tool: Tool) -> None:
        """Update visual state to show selected tool.

        Args:
            selected_tool: Tool to highlight
        """
        for button in self.query(".tool_button"):
            assert isinstance(button, Button)
            button_tool = self.tool_by_button[button]
            button.set_class(selected_tool == button_tool, "selected")
