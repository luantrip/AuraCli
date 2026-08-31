"""
Enhanced TextArea widget with auto-completion and smart editing.

Features:
- Auto-pairing for brackets, quotes, and markdown syntax
- Auto-indentation for lists and code blocks
- Line operations (duplicate, move up/down)
- Markdown-aware editing
"""

import re

from textual import events
from textual.widgets import TextArea


class AuraTextArea(TextArea):
    """
    TextArea with enhanced auto-completion and smart editing.

    Provides productivity features for markdown and code editing:
    - Auto-completion for brackets, quotes, markdown syntax
    - Smart indentation for lists and code blocks
    - Line manipulation operations
    """

    def __init__(self, *args, **kwargs):
        """Initialize the instance."""
        super().__init__(*args, **kwargs)
        self.auto_indent_enabled = True
        self.auto_pair_enabled = True

    def _get_current_line(self) -> str:
        """Get content of the current line."""
        cursor_row, _ = self.cursor_location
        lines = self.text.split("\n")
        if cursor_row < len(lines):
            return lines[cursor_row]
        return ""

    def _get_line_indent(self, line: str) -> str:
        """Get the indentation of a line."""
        match = re.match(r"^(\s*)", line)
        return match.group(1) if match else ""

    def _is_in_code_block(self) -> bool:
        """Check if cursor is inside a code block."""
        cursor_row, _ = self.cursor_location
        lines = self.text.split("\n")

        code_block_count = 0
        for i in range(cursor_row + 1):
            if i < len(lines) and lines[i].strip().startswith("```"):
                code_block_count += 1

        return code_block_count % 2 == 1

    def _handle_auto_indent(self, event: events.Key) -> bool:
        """Handle auto-indentation for lists and code blocks."""
        if not self.auto_indent_enabled or event.key != "enter":
            return False

        current_line = self._get_current_line()
        indent = self._get_line_indent(current_line)

        list_patterns = [
            (r"^(\s*)([-*+])\s+(.*)$", lambda m: f"{m.group(1)}{m.group(2)} "),
            (
                r"^(\s*)(\d+)\.\s+(.*)$",
                lambda m: f"{m.group(1)}{int(m.group(2)) + 1}. ",
            ),
            (r"^(\s*)(>\s*)(.*)$", lambda m: f"{m.group(1)}> "),
            (r"^(\s*)(-\s*\[[ x]\])\s+(.*)$", lambda m: f"{m.group(1)}- [ ] "),
        ]

        for pattern, replacement in list_patterns:
            match = re.match(pattern, current_line.rstrip())
            if match:
                content_group = 3 if len(match.groups()) >= 3 else 2
                content = (
                    match.group(content_group).strip()
                    if content_group <= len(match.groups())
                    else ""
                )

                if not content:
                    self.insert("\n")
                else:
                    new_indent = replacement(match)
                    self.insert(f"\n{new_indent}")

                event.prevent_default()
                return True

        if current_line.strip().startswith("```"):
            self.insert(f"\n{indent}")
            event.prevent_default()
            return True

        if indent:
            self.insert(f"\n{indent}")
            event.prevent_default()
            return True

        return False

    def _handle_auto_pair(self, event: events.Key) -> bool:
        """Handle auto-pairing with context awareness."""
        if not self.auto_pair_enabled:
            return False

        pairs = {
            "(": ")",
            "{": "}",
            "[": "]",
            '"': '"',
            "'": "'",
            "`": "`",
            "*": "*",
            "_": "_",
            "~": "~",
        }

        char = event.character
        if char not in pairs:
            return False

        _cursor_row, cursor_col = self.cursor_location
        current_line = self._get_current_line()

        if self._is_in_code_block() and char in ["*", "_", "~"]:
            return False

        if char in ["*", "_"]:
            before_cursor = current_line[:cursor_col]
            if before_cursor.endswith(char):
                self.insert(char + char)
                self.move_cursor_relative(columns=-1)
                event.prevent_default()
                return True

        if char == "`":
            before_cursor = current_line[:cursor_col]
            if before_cursor.endswith("``"):
                self.insert("`\n\n```")
                self.move_cursor_relative(rows=-1)
                event.prevent_default()
                return True

        self.insert(char + pairs[char])
        self.move_cursor_relative(columns=-1)
        event.prevent_default()
        return True

    def _handle_closing_pair(self, event: events.Key) -> bool:
        """Handle typing closing pair character."""
        closing_chars = ")}]\"'`"
        char = event.character

        if not char or char not in closing_chars:
            return False

        _cursor_row, cursor_col = self.cursor_location
        current_line = self._get_current_line()

        if cursor_col < len(current_line) and current_line[cursor_col] == char:
            self.move_cursor_relative(columns=1)
            event.prevent_default()
            return True

        return False

    def action_duplicate_line(self) -> None:
        """Duplicate the current line."""
        cursor_row, cursor_col = self.cursor_location
        lines = self.text.split("\n")

        if cursor_row < len(lines):
            current_line = lines[cursor_row]
            lines.insert(cursor_row + 1, current_line)
            self.text = "\n".join(lines)
            self.cursor_location = (cursor_row + 1, cursor_col)

    def action_move_line_up(self) -> None:
        """Move the current line up."""
        cursor_row, cursor_col = self.cursor_location
        lines = self.text.split("\n")

        if cursor_row > 0 and cursor_row < len(lines):
            lines[cursor_row], lines[cursor_row - 1] = (
                lines[cursor_row - 1],
                lines[cursor_row],
            )
            self.text = "\n".join(lines)
            self.cursor_location = (cursor_row - 1, cursor_col)

    def action_move_line_down(self) -> None:
        """Move the current line down."""
        cursor_row, cursor_col = self.cursor_location
        lines = self.text.split("\n")

        if cursor_row < len(lines) - 1:
            lines[cursor_row], lines[cursor_row + 1] = (
                lines[cursor_row + 1],
                lines[cursor_row],
            )
            self.text = "\n".join(lines)
            self.cursor_location = (cursor_row + 1, cursor_col)

    def action_delete_line(self) -> None:
        """Delete the current line."""
        cursor_row, _cursor_col = self.cursor_location
        lines = self.text.split("\n")

        if cursor_row < len(lines):
            lines.pop(cursor_row)
            self.text = "\n".join(lines) if lines else ""
            new_row = min(cursor_row, len(lines) - 1) if lines else 0
            self.cursor_location = (new_row, 0)

    def toggle_auto_indent(self) -> None:
        """Toggle auto-indent feature."""
        self.auto_indent_enabled = not self.auto_indent_enabled

    def toggle_auto_pair(self) -> None:
        """Toggle auto-pair feature."""
        self.auto_pair_enabled = not self.auto_pair_enabled

    async def _on_key(self, event: events.Key) -> None:
        """Handle key events for enhanced editing."""
        if self._handle_auto_indent(event):
            return

        if self._handle_closing_pair(event):
            return

        if self._handle_auto_pair(event):
            return

        await super()._on_key(event)
