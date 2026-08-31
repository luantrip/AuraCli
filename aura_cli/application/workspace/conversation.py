"""Conversation history model shared across runtime adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class ChatMessage:
    """Structured representation of a conversation message."""

    role: str
    content: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ChatMessage:
        return cls(**data)


class ConversationMemory:
    """Typed rolling conversation buffer with lightweight summarization."""

    def __init__(self, max_messages: int = 50, max_tokens: int = 8000):
        self.max_messages = max_messages
        self.max_tokens = max_tokens
        self.messages: List[ChatMessage] = []
        self.summary = ""
        self._total_chars = 0

    def add_message(
        self, role: str, content: str, metadata: Optional[Dict] = None
    ) -> None:
        message = ChatMessage(role=role, content=content, metadata=metadata or {})
        self.messages.append(message)
        self._total_chars += len(content)
        if len(self.messages) > self.max_messages:
            self._compress_history()

    def _compress_history(self) -> None:
        keep_count = self.max_messages // 2
        old_messages = self.messages[:-keep_count]
        self.messages = self.messages[-keep_count:]
        if old_messages:
            parts = [
                f"[{msg.role}]: {msg.content[:100]}..." for msg in old_messages[:10]
            ]
            self.summary = "Previous conversation summary:\n" + "\n".join(parts)

    def get_context(self, include_summary: bool = True) -> List[Dict[str, str]]:
        context = []
        if include_summary and self.summary:
            context.append({"role": "system", "content": self.summary})
        context.extend(
            {"role": msg.role, "content": msg.content} for msg in self.messages
        )
        return context

    def get_last_n(self, n: int) -> List[ChatMessage]:
        return self.messages[-n:] if n < len(self.messages) else self.messages

    def clear(self) -> None:
        self.messages = []
        self.summary = ""
        self._total_chars = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "messages": [message.to_dict() for message in self.messages],
            "summary": self.summary,
            "max_messages": self.max_messages,
            "max_tokens": self.max_tokens,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ConversationMemory:
        memory = cls(
            max_messages=data.get("max_messages", 50),
            max_tokens=data.get("max_tokens", 8000),
        )
        memory.messages = [
            ChatMessage.from_dict(message) for message in data.get("messages", [])
        ]
        memory.summary = data.get("summary", "")
        return memory
