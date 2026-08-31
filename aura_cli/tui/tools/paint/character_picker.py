"""Character Picker Dialog - Aura CLI Paint Tool.

Dialog window for selecting characters from Code Page 437 character set
with visual grid display and keyboard navigation.

Features:
    - Code Page 437 character grid (16x16)
    - Visual character selection
    - Keyboard navigation support
    - Special handling for null and space characters
"""

from typing import Any, Callable, ClassVar

from textual.widget import Widget
from textual.widgets import Button, DataTable

from aura_cli.application.paint.localization.i18n import get as _

from .windows import DialogWindow


class CharacterSelectorDialogWindow(DialogWindow):
    """Dialog for selecting characters from Code Page 437.

    Displays a 16x16 grid of characters for visual selection.
    Handles special cases like null (0x00) and space (0x20, 0xFF).

    Attributes:
        code_page_437: Complete Code Page 437 character set
        char_list: List of individual characters for grid display
    """

    # Code Page 437 character set
    # NUL (0), SP (32), and NBSP (255) are treated as space when selected
    # Null can cause screen malfunction if inserted into document
    code_page_437 = "\0☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼ !\"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~⌂ÇüéâäàåçêëèïîìÄÅÉæÆôöòûùÿÖÜ¢£¥₧ƒáíóúñÑªº¿⌐¬½¼¡«»░▒▓│┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌█▄▌▐▀αßΓπΣσµτΦΘΩδ∞φε∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■ "
    char_list: ClassVar[Any] = list(code_page_437)

    def __init__(
        self,
        *children: Widget,
        selected_character: str | None,
        handle_selected_character: Callable[[str], None],
        **kwargs: Any,
    ) -> None:
        """Initialize character selector dialog.

        Args:
            *children: Child widgets
            selected_character: Initially selected character
            handle_selected_character: Callback for character selection
            **kwargs: Additional dialog arguments
        """
        super().__init__(*children, handle_button=self.handle_button, **kwargs)
        self._selected_character: str | None = selected_character
        self.handle_selected_character = handle_selected_character

    def handle_button(self, button: Button) -> None:
        """Handle button press events.

        Args:
            button: Button that was pressed
        """
        if button.has_class("cancel"):
            self.request_close()
        else:
            if self._selected_character is None:
                return
            self.handle_selected_character(self._selected_character)

    def on_data_table_cell_highlighted(self, event: DataTable.CellHighlighted) -> None:
        """Handle cell highlight in character grid.

        Converts null character to space for safety.

        Args:
            event: Cell highlight event
        """
        self._selected_character = (
            event.value if isinstance(event.value, str) and event.value != "\0" else " "
        )

    def on_mount(self) -> None:
        """Initialize character grid on mount.

        Creates 16x16 DataTable with Code Page 437 characters
        and adds OK/Cancel buttons.
        """
        data_table: DataTable[str] = DataTable()
        column_count = 16
        data_table.add_columns(*([" "] * column_count))
        data_table.show_header = False
        for i in range(0, len(self.char_list), column_count):
            data_table.add_row(*self.char_list[i : i + column_count])
        self.content.mount(data_table)
        self.content.mount(Button(_("OK"), classes="ok submit"))
        self.content.mount(Button(_("Cancel"), classes="cancel"))
