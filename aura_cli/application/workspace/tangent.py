"""
Tangent mode manager for conversation checkpointing.

Enables exploring tangential topics without polluting main conversation.
"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class TangentState(Enum):
    """Tangent mode state."""

    NORMAL = "normal"
    TANGENT = "tangent"


@dataclass
class ConversationCheckpoint:
    """Conversation state checkpoint."""

    messages: List[Dict[str, Any]]
    timestamp: datetime
    description: str = "Tangent checkpoint"


class TangentManager:
    """
    Manages tangent mode for conversation checkpointing.

    Allows users to:
    - Enter tangent mode (create checkpoint)
    - Exit tangent mode (restore checkpoint)
    - Exit with tail (restore but keep last Q&A)
    - Forget last N messages

    Example:
        >>> manager = TangentManager()
        >>> manager.enter(conversation)
        "Created checkpoint (↯)"
        >>> # Ask tangential questions...
        >>> manager.exit(conversation)
        "Restored from checkpoint"
    """

    def __init__(
        self,
        forget_selector: Callable[[List[Dict[str, Any]]], Optional[int]] | None = None,
    ):
        """Initialize the instance."""
        self.checkpoint: Optional[ConversationCheckpoint] = None
        self.state = TangentState.NORMAL
        self._forget_selector = forget_selector

    @property
    def in_tangent(self) -> bool:
        """Check if currently in tangent mode."""
        return self.state == TangentState.TANGENT

    def enter(self, messages: List[Dict[str, Any]]) -> str:
        """
        Enter tangent mode by creating conversation checkpoint.

        Args:
            messages: Current conversation messages

        Returns:
            Status message
        """
        if self.in_tangent:
            return "Already in tangent mode. Use /tangent to exit first."

        self.checkpoint = ConversationCheckpoint(
            messages=deepcopy(messages),
            timestamp=datetime.now(),
            description="Tangent checkpoint",
        )

        self.state = TangentState.TANGENT

        return "Created checkpoint (↯). Use /tangent to restore conversation."

    def exit(
        self, messages: List[Dict[str, Any]], keep_tail: bool = False
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Exit tangent mode and restore checkpoint.

        Args:
            messages: Current conversation messages
            keep_tail: If True, preserve last Q&A pair

        Returns:
            Tuple of (restored_messages, status_message)
        """
        if not self.in_tangent:
            return messages, "Not in tangent mode."

        if self.checkpoint is None:
            return messages, "No checkpoint found."

        restored_messages = deepcopy(self.checkpoint.messages)

        if keep_tail and len(messages) > len(self.checkpoint.messages):
            new_messages = messages[len(self.checkpoint.messages) :]
            last_user_idx = None
            for i in range(len(new_messages) - 1, -1, -1):
                if new_messages[i].get("role") == "user":
                    last_user_idx = i
                    break

            if last_user_idx is not None:
                restored_messages.extend(new_messages[last_user_idx:])
                message = "Restored from checkpoint (↯) with last entry preserved."
            else:
                message = "Restored from checkpoint (↯)."
        else:
            message = "Restored from checkpoint (↯)."

        self.checkpoint = None
        self.state = TangentState.NORMAL

        return restored_messages, message

    def forget(
        self,
        messages: List[Dict[str, Any]],
        count: Optional[int] = None,
        interactive: bool = False,
    ) -> Tuple[List[Dict[str, Any]], str]:
        """
        Remove last N user messages (and their responses).

        A "message" is one user prompt and all assistant responses
        (including tool use) until the next user prompt.

        Args:
            messages: Current conversation messages
            count: Number of user messages to forget (None for interactive)
            interactive: If True and count is None, show interactive selection

        Returns:
            Tuple of (updated_messages, status_message)
        """
        user_messages = []
        for i, msg in enumerate(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                preview = content[:60] + "..." if len(content) > 60 else content
                preview = preview.replace("\n", " ")
                user_messages.append(
                    {"index": i, "preview": preview, "full_content": content}
                )

        if not user_messages:
            return messages, "No user messages to forget."

        if count is None:
            if interactive:
                count = (
                    self._forget_selector(user_messages)
                    if self._forget_selector is not None
                    else None
                )
                if count is None or count == 0:
                    return messages, "Cancelled forget operation."
            else:
                count = 1

        if count <= 0:
            return messages, "Count must be positive."

        if len(user_messages) < count:
            return messages, f"Only {len(user_messages)} user messages available."

        cutoff_idx = user_messages[-(count)]["index"]
        updated_messages = messages[:cutoff_idx]

        return updated_messages, f"Forgot last {count} message(s)."

    def get_indicator(self) -> str:
        """
        Get visual indicator for tangent mode.

        Returns:
            "↯" if in tangent mode, "" otherwise
        """
        return "↯" if self.in_tangent else ""

    def reset(self):
        """Reset tangent manager state."""
        self.checkpoint = None
        self.state = TangentState.NORMAL
