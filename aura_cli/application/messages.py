"""Presentation-neutral chat message contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    ERROR = "error"
    SUCCESS = "success"
    TOOL = "tool"
    THINKING = "thinking"


@dataclass
class Reaction:
    emoji: str
    count: int = 1
    users: List[str] = field(default_factory=list)


@dataclass
class MessageMetadata:
    tokens: Optional[int] = None
    model: Optional[str] = None
    duration: Optional[float] = None
    tool_name: Optional[str] = None
    is_streaming: bool = False
    is_edited: bool = False
    reply_to: Optional[str] = None
    thread_id: Optional[str] = None
