"""
Context menu components for the chat system.

Provides lightweight action menu support for message bubbles, allowing
users to copy, react, and perform quick actions on messages.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, ClassVar, Dict, List, Optional


class ActionType(Enum):
    """Types of context menu actions."""

    COPY = "copy"
    REACT = "react"
    REPLY = "reply"
    EDIT = "edit"
    DELETE = "delete"
    PIN = "pin"
    SHARE = "share"
    INSPECT = "inspect"
    REGENERATE = "regenerate"
    CUSTOM = "custom"


@dataclass
class ContextAction:
    """
    A single action in a context menu.

    Attributes:
        action_type: Type of action
        label: Display label
        icon: Optional icon character
        shortcut: Optional keyboard shortcut hint
        handler: Optional callable to invoke
        enabled: Whether the action is enabled
        metadata: Extra data passed to handler
    """

    action_type: ActionType
    label: str
    icon: str = ""
    shortcut: str = ""
    handler: Optional[Callable[..., Any]] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def execute(self, **kwargs: Any) -> Any:
        """Execute the action handler if set."""
        if self.handler and self.enabled:
            return self.handler(**{**self.metadata, **kwargs})
        return None


@dataclass
class ContextMenu:
    """
    A context menu container for message actions.

    Attributes:
        title: Optional menu title
        actions: List of available actions
    """

    title: str = ""
    actions: List[ContextAction] = field(default_factory=list)

    def add_action(self, action: ContextAction) -> "ContextMenu":
        """Add an action and return self for chaining."""
        self.actions.append(action)
        return self

    def get_action(self, action_type: ActionType) -> Optional[ContextAction]:
        """Return the first action of the given type, or None."""
        return next(
            (a for a in self.actions if a.action_type == action_type),
            None,
        )

    def enabled_actions(self) -> List[ContextAction]:
        """Return only enabled actions."""
        return [a for a in self.actions if a.enabled]


class QuickReactions:
    """Common emoji reactions for messages."""

    THUMBS_UP = "👍"
    THUMBS_DOWN = "👎"
    HEART = "❤️"
    LAUGH = "😂"
    SURPRISED = "😮"
    SAD = "😢"
    FIRE = "🔥"
    CHECK = "✅"

    DEFAULT_SET: ClassVar[List[str]] = [
        THUMBS_UP,
        THUMBS_DOWN,
        HEART,
        LAUGH,
        FIRE,
        CHECK,
    ]


def create_message_actions(
    message_id: str,
    can_edit: bool = False,
    can_delete: bool = False,
    can_regenerate: bool = False,
    on_copy: Optional[Callable[..., Any]] = None,
    on_react: Optional[Callable[..., Any]] = None,
    on_reply: Optional[Callable[..., Any]] = None,
    on_edit: Optional[Callable[..., Any]] = None,
    on_delete: Optional[Callable[..., Any]] = None,
    on_regenerate: Optional[Callable[..., Any]] = None,
) -> ContextMenu:
    """
    Build a standard message context menu.

    Args:
        message_id: ID of the message this menu belongs to.
        can_edit: Whether the edit action should be enabled.
        can_delete: Whether the delete action should be enabled.
        can_regenerate: Whether the regenerate action should be shown.
        on_*: Optional handlers for each action.

    Returns:
        A ContextMenu populated with the standard message actions.
    """
    menu = ContextMenu(title=f"Message {message_id}")

    menu.add_action(
        ContextAction(
            action_type=ActionType.COPY,
            label="Copy",
            icon="📋",
            shortcut="Ctrl+C",
            handler=on_copy,
            metadata={"message_id": message_id},
        )
    )
    menu.add_action(
        ContextAction(
            action_type=ActionType.REACT,
            label="React",
            icon="😊",
            handler=on_react,
            metadata={"message_id": message_id},
        )
    )
    menu.add_action(
        ContextAction(
            action_type=ActionType.REPLY,
            label="Reply",
            icon="↩️",
            handler=on_reply,
            metadata={"message_id": message_id},
        )
    )
    menu.add_action(
        ContextAction(
            action_type=ActionType.EDIT,
            label="Edit",
            icon="✏️",
            handler=on_edit,
            enabled=can_edit,
            metadata={"message_id": message_id},
        )
    )
    menu.add_action(
        ContextAction(
            action_type=ActionType.DELETE,
            label="Delete",
            icon="🗑️",
            handler=on_delete,
            enabled=can_delete,
            metadata={"message_id": message_id},
        )
    )
    if can_regenerate:
        menu.add_action(
            ContextAction(
                action_type=ActionType.REGENERATE,
                label="Regenerate",
                icon="🔄",
                handler=on_regenerate,
                metadata={"message_id": message_id},
            )
        )

    return menu
