"""
Rich Prompt Input Widget for Aura TUI.

Implements an advanced input widget with:
- Rich parts (files, images, pasted text) as embedded placeholders
- Smart paste detection
- External editor integration
- Multi-line support
- History navigation
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import logging
import os
from pathlib import Path
import tempfile
from typing import Any, Callable, ClassVar, Dict, List, Literal, Optional

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Input, Label, Static

from aura_cli.tui.utils.clipboard_utils import ClipboardContent, ClipboardManager

logger = logging.getLogger(__name__)


@dataclass
class PromptPart:
    """
    A rich part embedded in the prompt.

    Parts are displayed as placeholders but expand to
    their full content when the prompt is submitted.
    """

    type: Literal["file", "image", "pasted", "agent", "tool"]
    data: Dict[str, Any]
    placeholder: str
    id: str = ""
    start_pos: int = 0
    end_pos: int = 0

    def __post_init__(self):
        """Post-initialization setup for dataclass fields."""
        if not self.id:
            import uuid

            self.id = str(uuid.uuid4())[:8]

    @property
    def display(self) -> str:
        """Get display text for the placeholder."""
        icons = {
            "file": "◇",
            "image": "◇",
            "pasted": "✎",
            "agent": "◈",
            "tool": "⚒",
        }
        icon = icons.get(self.type, "◇")
        return f"[{icon} {self.placeholder}]"

    def expand(self) -> str:
        """Expand the part to its full content."""
        if self.type == "file":
            path = self.data.get("path", "")
            try:
                return Path(path).expanduser().read_text()
            except Exception as e:
                logger.error(f"Failed to read file {path}: {e}")
                return f"[Error reading file: {path}]"

        elif self.type == "pasted":
            return self.data.get("content", "")

        elif self.type == "image":
            # Return base64 or path reference
            if "base64" in self.data:
                return f"[Image: base64 data, {len(self.data['base64'])} chars]"
            return f"[Image: {self.data.get('path', 'unknown')}]"

        elif self.type == "agent":
            return f"@{self.data.get('agent_name', 'agent')}"

        elif self.type == "tool":
            return f"/{self.data.get('tool_name', 'tool')}"

        return self.placeholder


@dataclass
class PromptState:
    """State of the prompt input."""

    raw_text: str = ""
    parts: List[PromptPart] = field(default_factory=list)
    cursor_position: int = 0
    history_index: int = -1
    mode: Literal["normal", "shell", "multiline"] = "normal"


class RichPromptInput(Static):
    """
    Advanced prompt input with rich part support.

    Features:
    - File/image paste detection with placeholders
    - Large text summarization
    - External editor integration (Ctrl+E)
    - Command history navigation
    - Multi-line mode (triple quotes)

    Example:
        ```python
        prompt = RichPromptInput(
            placeholder="Type a command...",
            on_submit=handle_submit
        )

        # Get expanded content
        full_content = prompt.get_full_prompt()
        ```
    """

    BINDINGS: ClassVar[list] = [
        Binding("ctrl+e", "open_editor", "External Editor", show=False),
        Binding("ctrl+v", "smart_paste", "Smart Paste", show=False),
        Binding("ctrl+u", "clear_input", "Limpar", show=False),
        Binding("up", "history_prev", "Previous", show=False),
        Binding("down", "history_next", "Next", show=False),
    ]

    # Reactive state
    value = reactive("")
    mode = reactive("normal")

    class Submitted(Message):
        """Emitted when prompt is submitted."""

        def __init__(self, content: str, parts: List[PromptPart]):
            """Initialize the instance."""
            super().__init__()
            self.content = content
            self.parts = parts
            self.full_content = content  # Will be expanded

    class PartAdded(Message):
        """Emitted when a part is added."""

        def __init__(self, part: PromptPart):
            """Initialize the instance."""
            super().__init__()
            self.part = part

    def __init__(
        self,
        placeholder: str = "Type a command...",
        on_submit: Optional[Callable[[str, List[PromptPart]], None]] = None,
        **kwargs,
    ):
        """
        Initialize the rich prompt.

        Args:
            placeholder: Placeholder text
            on_submit: Callback for submission
        """
        super().__init__(**kwargs)
        self.placeholder = placeholder
        self.on_submit = on_submit

        self.state = PromptState()
        self.history: List[str] = []
        self._clipboard = ClipboardManager()
        self._parts_counter = {"file": 0, "image": 0, "pasted": 0}

    def compose(self) -> ComposeResult:
        """Compose the prompt widget."""
        with Horizontal():
            yield Static("› ", classes="prompt-prefix")
            yield Input(
                placeholder=self.placeholder,
                id="rich_input_field",
                classes="prompt-input",
            )
        yield Horizontal(id="parts_display", classes="prompt-parts")

    def on_mount(self) -> None:
        """Focus input on mount."""
        self.query_one("#rich_input_field", Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission."""
        if event.input.id == "rich_input_field":
            content = event.value.strip()

            # Check for multiline mode toggle
            if content == '"""' or content == "'''":
                self._toggle_multiline()
                event.input.value = ""
                return

            if not content and not self.state.parts:
                return

            # Add to history
            if content:
                self.history.append(content)

            # Build full content with expanded parts
            full_content = self._expand_content(content)

            # Clear input
            event.input.value = ""
            self.state.parts.clear()
            self._update_parts_display()

            # Emit message
            self.post_message(self.Submitted(content, self.state.parts.copy()))

            # Call callback if provided
            if self.on_submit:
                self.on_submit(full_content, self.state.parts)

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes."""
        if event.input.id == "rich_input_field":
            self.value = event.value
            self.state.raw_text = event.value

    async def action_smart_paste(self) -> None:
        """Handle smart paste."""
        content = self._clipboard.paste_smart()
        if not content:
            return

        input_field = self.query_one("#rich_input_field", Input)

        if content.is_file_path:
            await self._handle_file_paste(content)
        elif content.is_large_text:
            await self._handle_large_text_paste(content)
        elif content.is_image:
            await self._handle_image_paste(content)
        else:
            # Regular paste
            input_field.insert_text_at_cursor(content.content)

    async def _handle_file_paste(self, content: ClipboardContent) -> None:
        """Handle file path paste."""
        path = Path(content.content).expanduser()

        if not path.exists():
            self.app.notify(f"File not found: {path}", severity="warning")
            return

        self._parts_counter["file"] += 1
        part = PromptPart(
            type="file",
            data={
                "path": str(path),
                "size": path.stat().st_size if path.is_file() else 0,
            },
            placeholder=f"{path.name}",
        )

        self._insert_part(part)

    async def _handle_large_text_paste(self, content: ClipboardContent) -> None:
        """Handle large text paste."""
        lines = content.metadata.get("lines", 0)
        chars = content.metadata.get("characters", 0)

        self._parts_counter["pasted"] += 1
        num = self._parts_counter["pasted"]

        part = PromptPart(
            type="pasted",
            data={"content": content.content, "lines": lines, "characters": chars},
            placeholder=f"Pasted {num} (~{lines} lines)",
        )

        self._insert_part(part)

    async def _handle_image_paste(self, content: ClipboardContent) -> None:
        """Handle image paste."""
        path = content.content

        self._parts_counter["image"] += 1
        num = self._parts_counter["image"]

        # Read and encode image
        try:
            base64_data = self._clipboard.read_file_as_base64(path)
            part = PromptPart(
                type="image",
                data={"path": path, "base64": base64_data},
                placeholder=f"Image {num}",
            )
            self._insert_part(part)
        except Exception as e:
            self.app.notify(f"Failed to load image: {e}", severity="error")

    def _insert_part(self, part: PromptPart) -> None:
        """Insert a part into the prompt."""
        input_field = self.query_one("#rich_input_field", Input)

        # Add part
        self.state.parts.append(part)

        # Insert placeholder at cursor
        input_field.insert_text_at_cursor(part.display)

        # Update display
        self._update_parts_display()

        # Emit message
        self.post_message(self.PartAdded(part))

        self.app.notify(f"Added: {part.placeholder}", severity="information", timeout=2)

    def _update_parts_display(self) -> None:
        """Update the parts display area."""
        parts_display = self.query_one("#parts_display", Horizontal)
        parts_display.remove_children()

        if not self.state.parts:
            return

        parts_display.mount(Label("Attached: ", classes="part-attached-label"))

        for i, part in enumerate(self.state.parts):
            if i > 0:
                parts_display.mount(Label(", ", classes="part-separator"))

            icon = {"file": "◇", "image": "◇", "pasted": "✎"}.get(part.type, "◇")
            parts_display.mount(
                Label(f"{icon} {part.placeholder}", classes="part-label")
            )

    def _expand_content(self, raw_content: str) -> str:
        """Expand all parts to full content."""
        result = raw_content

        # Replace placeholders with expanded content
        for part in self.state.parts:
            result = result.replace(part.display, part.expand())

        return result

    def _toggle_multiline(self) -> None:
        """Toggle multiline mode."""
        if self.mode == "multiline":
            self.mode = "normal"
            self.remove_class("-multiline")
            self.app.notify("Multiline mode off", timeout=1)
        else:
            self.mode = "multiline"
            self.add_class("-multiline")
            self.app.notify('Multiline mode on (use """ to exit)', timeout=2)

    async def action_open_editor(self) -> None:
        """Open content in external editor."""
        editor = os.environ.get("EDITOR", "nano")

        input_field = self.query_one("#rich_input_field", Input)
        content = input_field.value

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            # Open editor (blocking)
            import subprocess

            subprocess.run([editor, temp_path])

            # Read back
            with open(temp_path) as f:
                new_content = f.read().strip()

            input_field.value = new_content
            self.app.notify("Content updated from editor", timeout=2)
        except Exception as e:
            self.app.notify(f"Editor error: {e}", severity="error")
        finally:
            with contextlib.suppress(Exception):
                os.unlink(temp_path)

    def action_clear_input(self) -> None:
        """Clear the input."""
        input_field = self.query_one("#rich_input_field", Input)
        input_field.value = ""
        self.state.parts.clear()
        self._update_parts_display()

    def action_history_prev(self) -> None:
        """Navigate to previous history item."""
        if not self.history:
            return

        if self.state.history_index < len(self.history) - 1:
            self.state.history_index += 1
            input_field = self.query_one("#rich_input_field", Input)
            input_field.value = self.history[-(self.state.history_index + 1)]

    def action_history_next(self) -> None:
        """Navigate to next history item."""
        if self.state.history_index > 0:
            self.state.history_index -= 1
            input_field = self.query_one("#rich_input_field", Input)
            input_field.value = self.history[-(self.state.history_index + 1)]
        elif self.state.history_index == 0:
            self.state.history_index = -1
            input_field = self.query_one("#rich_input_field", Input)
            input_field.value = ""

    def get_full_prompt(self) -> str:
        """Get the full expanded prompt content."""
        input_field = self.query_one("#rich_input_field", Input)
        return self._expand_content(input_field.value)

    @property
    def parts(self) -> List[PromptPart]:
        """Get current parts."""
        return self.state.parts.copy()

    def focus(self) -> None:  # type: ignore[override]
        """Focus the input field."""
        self.query_one("#rich_input_field", Input).focus()

    def clear(self) -> None:
        """Clear input and parts."""
        self.action_clear_input()

    def set_value(self, value: str) -> None:
        """Set the input value."""
        self.query_one("#rich_input_field", Input).value = value
