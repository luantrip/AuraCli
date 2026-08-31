"""Layer Management Panel - Aura CLI Paint Tool.

Professional interface for managing multiple layers in ANSI art documents
with real-time synchronization and visual feedback.

Features:
    - Hierarchical layer list display
    - Layer visibility toggling with icons
    - Layer reordering (move up/down)
    - Add/delete layer operations
    - Active layer selection and highlighting
    - Real-time synchronization with LayerStack
    - Professional styling with Aura color palette
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, ListItem, ListView, Static

if TYPE_CHECKING:
    from aura_cli.application.paint.layers import LayerStack


class LayerListItem(ListItem):
    """
    Individual layer item in the layer list.

    Displays layer name and visibility status with professional styling.
    """

    def __init__(
        self,
        layer_id: str,
        layer_name: str,
        visible: bool = True,
        is_active: bool = False,
    ) -> None:
        """
        Initialize layer list item.

        Args:
            layer_id: Unique identifier for the layer
            layer_name: Display name of the layer
            visible: Whether the layer is visible
            is_active: Whether this is the currently active layer
        """
        super().__init__()
        self.layer_id = layer_id
        self.layer_name = layer_name
        self.visible = visible
        self.is_active = is_active

    def compose(self) -> ComposeResult:
        """Compose the layer item with visibility indicator and name."""
        # Visibility icon
        visibility_icon = "●" if self.visible else "○"

        # Active indicator
        active_marker = "▶" if self.is_active else " "

        # Compose label with proper formatting
        label_text = f"{active_marker} {visibility_icon} {self.layer_name}"
        yield Label(label_text)


class LayerManagementPanel(Container):
    """
    Professional layer management panel for Paint Tool.

    Features:
    - Hierarchical layer list display
    - Layer visibility toggling
    - Layer reordering (move up/down)
    - Add/delete layer operations
    - Active layer selection
    - Real-time synchronization with LayerStack backend

    Messages:
    - LayerSelected: Emitted when a layer is selected
    - LayerAdded: Emitted when add layer is requested
    - LayerDeleted: Emitted when delete layer is requested
    - LayerMoved: Emitted when layer reorder is requested
    - LayerVisibilityToggled: Emitted when visibility is toggled
    """

    DEFAULT_CSS = """
    LayerManagementPanel {
        width: 22;
        height: 100%;
        border: solid $primary;
        background: $surface;
        padding: 0;
    }

    LayerManagementPanel .panel-header {
        width: 100%;
        height: 1;
        background: $primary;
        color: $text;
        content-align: center middle;
        text-style: bold;
    }

    LayerManagementPanel Vertical {
        height: 100%;
        padding: 0;
    }

    LayerManagementPanel ListView {
        height: 1fr;
        border: none;
        background: $surface;
        padding: 0 1;
    }

    LayerManagementPanel .layer-controls {
        height: auto;
        layout: horizontal;
        background: $surface-darken-1;
        padding: 1;
    }

    LayerManagementPanel Button {
        width: 1fr;
        min-width: 5;
        height: 3;
    }

    LayerManagementPanel Button.success {
        background: $success;
    }

    LayerManagementPanel Button.error {
        background: $error;
    }
    """

    # Reactive properties
    layer_stack: reactive[Optional[LayerStack]] = reactive(None)
    active_layer_id: reactive[Optional[str]] = reactive(None)

    # Custom messages
    class LayerSelected(Message):
        """Emitted when a layer is selected."""

        def __init__(self, layer_id: str) -> None:
            super().__init__()
            self.layer_id = layer_id

    class LayerAdded(Message):
        """Emitted when add layer button is pressed."""

    class LayerDeleted(Message):
        """Emitted when delete layer is requested."""

        def __init__(self, layer_id: str) -> None:
            super().__init__()
            self.layer_id = layer_id

    class LayerMoved(Message):
        """Emitted when layer reorder is requested."""

        def __init__(self, layer_id: str, direction: int) -> None:
            """
            Initialize layer moved message.

            Args:
                layer_id: ID of the layer to move
                direction: Direction to move (-1 = down, +1 = up)
            """
            super().__init__()
            self.layer_id = layer_id
            self.direction = direction

    class LayerVisibilityToggled(Message):
        """Emitted when layer visibility is toggled."""

        def __init__(self, layer_id: str) -> None:
            super().__init__()
            self.layer_id = layer_id

    def compose(self) -> ComposeResult:
        """Compose the layer management panel."""
        with Vertical():
            yield Static("◆ LAYERS", classes="panel-header")
            yield ListView(id="layer-list")
            with Container(classes="layer-controls"):
                yield Button(
                    "+", id="btn-add-layer", variant="success", tooltip="Add Layer"
                )
                yield Button(
                    "-", id="btn-delete-layer", variant="error", tooltip="Delete Layer"
                )
                yield Button("↑", id="btn-move-up", tooltip="Move Up")
                yield Button("↓", id="btn-move-down", tooltip="Move Down")

    def refresh_layers(self, layer_stack: LayerStack) -> None:
        """
        Refresh the layer list from the layer stack.

        Args:
            layer_stack: The LayerStack to display
        """
        self.layer_stack = layer_stack
        self.active_layer_id = (
            layer_stack.active_layer.id if layer_stack.active_layer else None
        )

        list_view = self.query_one("#layer-list", ListView)
        list_view.clear()

        # Add layers in reverse order (top to bottom in UI)
        layers = layer_stack.get_layers_in_order()
        for layer in reversed(layers):
            is_active = layer.id == self.active_layer_id
            item = LayerListItem(
                layer_id=layer.id,
                layer_name=layer.name,
                visible=layer.visible,
                is_active=is_active,
            )
            list_view.append(item)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle layer selection from list."""
        if isinstance(event.item, LayerListItem):
            self.active_layer_id = event.item.layer_id
            self.post_message(self.LayerSelected(event.item.layer_id))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for layer operations."""
        button_id = event.button.id

        if button_id == "btn-add-layer":
            self.post_message(self.LayerAdded())

        elif button_id == "btn-delete-layer":
            self._handle_delete_layer()

        elif button_id in ("btn-move-up", "btn-move-down"):
            self._handle_move_layer(button_id)

    def _handle_delete_layer(self) -> None:
        """Handle delete layer button press."""
        list_view = self.query_one("#layer-list", ListView)
        if list_view.index is not None:
            item = list_view.highlighted_child
            if isinstance(item, LayerListItem):
                self.post_message(self.LayerDeleted(item.layer_id))

    def _handle_move_layer(self, button_id: str) -> None:
        """Handle move layer button press."""
        list_view = self.query_one("#layer-list", ListView)
        if list_view.index is not None:
            item = list_view.highlighted_child
            if isinstance(item, LayerListItem):
                direction = 1 if button_id == "btn-move-up" else -1
                self.post_message(self.LayerMoved(item.layer_id, direction))

    def get_selected_layer_id(self) -> Optional[str]:
        """
        Get the currently selected layer ID.

        Returns:
            The selected layer ID, or None if no selection
        """
        list_view = self.query_one("#layer-list", ListView)
        if list_view.index is not None:
            item = list_view.highlighted_child
            if isinstance(item, LayerListItem):
                return item.layer_id
        return None
