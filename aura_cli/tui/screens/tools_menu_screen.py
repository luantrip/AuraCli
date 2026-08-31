"""Tools Menu Screen - Optional launcher menu for auxiliary TUI tools.

Provides a navigable launcher interface for optional tools outside the main
chat/delegation flow:
- Paint: ANSI art editor launcher
- File Manager: dual-pane file browser launcher
- Monitor: terminal browser launcher
"""

from typing import ClassVar, List

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import (
    CenterMiddle,
    Container,
    Grid,
    HorizontalGroup,
    VerticalGroup,
)
from textual.message import Message
from textual.screen import Screen
from textual.widgets import Static

from aura_cli.tui.shell.base_tool_screen import pop_screen_and_restore_focus
from aura_cli.tui.tools import ToolAvailability, get_tool_availability
from aura_cli.tui.widgets.layout.tool_screen_chrome import ToolScreenChrome


class ToolItem:
    """Represents a tool in the menu."""

    def __init__(
        self,
        widget_id: str,
        name: str,
        description: str,
        available: bool,
        action_name: str,
        category: str = "Tools",
        icon: str = "⚒",
    ):
        """Initialize a tool item.

        Args:
            widget_id: Unique widget identifier
            name: Display name of the tool
            description: Short description
            available: Whether the tool is installed and usable
            action_name: App action to invoke on selection
            category: Tool category for grouping
            icon: Display icon character
        """
        self.name = name
        self.description = description
        self.available = available
        self.action_name = action_name
        self.category = category
        self.icon = icon
        self.widget_id = widget_id

    @property
    def id(self) -> str:
        """Widget id alias for ToolCard selection."""
        return self.widget_id


class ToolCard(Container):
    """Clickable card widget for a tool."""

    class ToolSelected(Message):
        """Message sent when tool is selected."""

        def __init__(self, tool_id: str):
            """Initialize with the selected tool ID."""
            super().__init__()
            self.tool_id = tool_id

    def __init__(self, tool: ToolItem, **kwargs):
        """Initialize the tool card widget.

        Args:
            tool: ToolItem data to display
        """
        super().__init__(**kwargs)
        self.can_focus = True
        self.tool = tool
        self.add_class("tool-card")
        if not tool.available:
            self.add_class("unavailable")

    def compose(self) -> ComposeResult:
        """Compose the tool card."""
        with VerticalGroup():
            with HorizontalGroup():
                yield Static(self.tool.icon, classes="tool-icon-large")
                with VerticalGroup():
                    yield Static(self.tool.name, classes="tool-card-name")
                    yield Static(
                        self.tool.description[:30] + "..."
                        if len(self.tool.description) > 30
                        else self.tool.description,
                        classes="tool-card-description",
                    )
            with HorizontalGroup(classes="tool-card-footer"):
                if self.tool.available:
                    yield Static("✓ Disponível", classes="tool-status-badge available")
                else:
                    yield Static(
                        "○ Indisponível", classes="tool-status-badge unavailable"
                    )

    async def on_click(self, event) -> None:
        """Handle click event."""
        if self.tool.available:
            self.post_message(self.ToolSelected(self.tool.id))

    def on_enter(self, event) -> None:
        """Handle mouse enter."""
        if event.node is self:
            self.add_class("hover")

    def on_leave(self, event) -> None:
        """Handle mouse leave."""
        if event.node is self:
            self.remove_class("hover")


class ToolsMenuScreen(Screen):
    """Launcher screen for optional auxiliary tools.

    This screen is intentionally lateral to the main Aura TUI workflow.
    """

    BINDINGS: ClassVar[list] = [
        Binding("escape", "return_to_chat", "Voltar", show=True),
        Binding("q", "return_to_chat", "Voltar", show=False),
        Binding("enter", "select_tool", "Selecionar", show=True),
        Binding("up", "move_up", "Subir", show=False),
        Binding("down", "move_down", "Descer", show=False),
        Binding("left", "move_left", "Esquerda", show=False),
        Binding("right", "move_right", "Direita", show=False),
    ]

    def __init__(self, **kwargs):
        """Initialize the tools menu screen."""
        super().__init__(**kwargs)
        self.tools: List[ToolItem] = []
        self.selected_index: int = 0
        self.tool_availability = ToolAvailability(False, False, False)
        self._initialize_tools()

    def _initialize_tools(self) -> None:
        """Initialize list of available tools."""
        self.tool_availability = get_tool_availability()

        # First item: Aura (back to chat)
        self.tools = [
            ToolItem(
                widget_id="aura",
                name="Aura",
                description="Voltar para a conversa principal",
                available=True,
                action_name="action_back_to_chat",
                category="Main",
                icon="✦",
            ),
            ToolItem(
                widget_id="paint",
                name="Paint",
                description="Editor de arte ANSI com animação, ferramentas e camadas",
                available=self.tool_availability.paint,
                action_name="action_push_paint_screen",
                category="Creative",
                icon="◐",
            ),
            ToolItem(
                widget_id="file_manager",
                name="Arquivos",
                description="Navegador de arquivos com operações e pré-visualização",
                available=self.tool_availability.files,
                action_name="action_push_file_manager_screen",
                category="System",
                icon="▷",
            ),
            ToolItem(
                widget_id="monitor",
                name="Monitor",
                description="Navegador web de terminal para acompanhar conteúdo",
                available=self.tool_availability.monitor,
                action_name="action_push_monitor_screen",
                category="System",
                icon="◎",
            ),
            ToolItem(
                widget_id="sessions",
                name="Histórico",
                description="Consultar e pesquisar sessões anteriores da Aura",
                available=True,
                action_name="action_push_history_screen",
                category="Main",
                icon="◇",
            ),
        ]

    def compose(self) -> ComposeResult:
        """Compose the tools menu screen."""
        with CenterMiddle():
            with VerticalGroup(
                id="tools_container", classes="tools-container aura-tool-screen"
            ):
                yield ToolScreenChrome(
                    "Aura CLI · Ferramentas",
                    "Paint · Arquivos · Monitor",
                )
                yield Static(
                    (
                        "Ferramentas opcionais verificadas agora."
                        if self.tool_availability.any_available
                        else "Nenhuma ferramenta opcional disponível neste ambiente."
                    ),
                    classes="tools-availability-summary",
                )

                # Grid layout for cards (3 columns, auto rows)
                with Grid(id="tools_grid", classes="tools-grid"):
                    for i, tool in enumerate(self.tools):
                        card = ToolCard(tool, id=f"tool_card_{i}")
                        if i == self.selected_index:
                            card.add_class("selected")
                        yield card

                with HorizontalGroup(classes="action-hint"):
                    yield Static("↑↓←→", classes="action-key")
                    yield Static(" navegar · ", classes="action-hint-text")
                    yield Static("Enter", classes="action-key")
                    yield Static(" selecionar · ", classes="action-hint-text")
                    yield Static("Esc", classes="action-key")
                    yield Static(" voltar", classes="action-hint-text")

    def on_mount(self) -> None:
        """Initialize screen state."""
        self._update_selection()

    def _update_selection(self) -> None:
        """Update visual selection state."""
        for i in range(len(self.tools)):
            try:
                card = self.query_one(f"#tool_card_{i}", ToolCard)
                if i == self.selected_index:
                    card.add_class("selected")
                else:
                    card.remove_class("selected")
            except Exception as error:
                self.log.debug("Tool card %s is not mounted yet: %s", i, error)

        # Scroll to selected item
        try:
            selected_card = self.query_one(
                f"#tool_card_{self.selected_index}", ToolCard
            )
            selected_card.scroll_visible()
            selected_card.focus()
        except Exception as error:
            self.log.debug("Selected tool card is not mounted yet: %s", error)

    def on_tool_card_tool_selected(self, message: ToolCard.ToolSelected) -> None:
        """Handle tool card selection message."""
        # Find the tool index
        for i, tool in enumerate(self.tools):
            if tool.id == message.tool_id:
                self.selected_index = i
                self._update_selection()
                self.action_select_tool()
                break

    def action_move_up(self) -> None:
        """Move selection up (previous row in grid)."""
        if self.selected_index >= 3:  # Grid has 3 columns
            self.selected_index -= 3
            self._update_selection()
        elif self.selected_index > 0:
            self.selected_index = 0
            self._update_selection()

    def action_move_down(self) -> None:
        """Move selection down (next row in grid)."""
        if self.selected_index < len(self.tools) - 3:  # Grid has 3 columns
            self.selected_index += 3
            if self.selected_index >= len(self.tools):
                self.selected_index = len(self.tools) - 1
            self._update_selection()
        elif self.selected_index < len(self.tools) - 1:
            self.selected_index = len(self.tools) - 1
            self._update_selection()

    def action_move_left(self) -> None:
        """Move selection left (previous column in grid)."""
        if self.selected_index > 0:
            self.selected_index -= 1
            self._update_selection()

    def action_move_right(self) -> None:
        """Move selection right (next column in grid)."""
        if self.selected_index < len(self.tools) - 1:
            self.selected_index += 1
            self._update_selection()

    def action_return_to_chat(self) -> None:
        """Leave the launcher and restore the main composer focus."""
        pop_screen_and_restore_focus(self.app)

    def action_select_tool(self) -> None:
        """Select and launch the currently selected tool."""
        if 0 <= self.selected_index < len(self.tools):
            tool = self.tools[self.selected_index]
            if tool.available:
                if tool.id == "aura":
                    self.action_return_to_chat()
                    return
                pop_screen_and_restore_focus(self.app)
                if hasattr(self.app, tool.action_name):
                    action = getattr(self.app, tool.action_name)
                    action()
            else:
                self.notify(
                    f"{tool.name} indisponível. Instale a dependência necessária e tente novamente.",
                    severity="warning",
                )

    @staticmethod
    def _consume_key(event) -> None:
        """Prevent a navigation key from reaching a second binding."""
        event.prevent_default()
        event.stop()

    def on_key(self, event) -> None:
        """Handle key events for navigation."""
        if event.key == "enter":
            self.action_select_tool()
            self._consume_key(event)
        elif event.key == "up":
            self.action_move_up()
            self._consume_key(event)
        elif event.key == "down":
            self.action_move_down()
            self._consume_key(event)
        elif event.key == "left":
            self.action_move_left()
            self._consume_key(event)
        elif event.key == "right":
            self.action_move_right()
            self._consume_key(event)
