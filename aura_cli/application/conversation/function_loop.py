"""State machine policies for an LLM function-calling turn."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FunctionLoopAction(Enum):
    EMPTY_RESPONSE = "empty_response"
    INVALID_RESPONSE = "invalid_response"
    EXECUTE_TOOLS = "execute_tools"
    RETRY_WITHOUT_TOOLS = "retry_without_tools"
    RETURN_CONTENT = "return_content"


@dataclass
class FunctionLoopBudget:
    """Track the number of individual tool calls consumed by a turn."""

    maximum: int = 5
    consumed: int = 0

    def __post_init__(self) -> None:
        if self.maximum < 0:
            raise ValueError("maximum function calls cannot be negative")

    @property
    def available(self) -> bool:
        return self.consumed < self.maximum

    def consume(self, count: int = 1) -> int:
        if count < 0:
            raise ValueError("consumed function-call count cannot be negative")
        self.consumed += count
        return self.consumed


def decide_function_loop_action(
    *,
    has_response: bool,
    has_choices: bool,
    tool_call_count: int,
    content: str | None,
    has_tool_schemas: bool,
) -> FunctionLoopAction:
    """Classify a provider response without importing provider-specific types."""
    if not has_response:
        return FunctionLoopAction.EMPTY_RESPONSE
    if not has_choices:
        return FunctionLoopAction.INVALID_RESPONSE
    if tool_call_count:
        return FunctionLoopAction.EXECUTE_TOOLS
    if not content and has_tool_schemas:
        return FunctionLoopAction.RETRY_WITHOUT_TOOLS
    return FunctionLoopAction.RETURN_CONTENT


__all__ = [
    "FunctionLoopAction",
    "FunctionLoopBudget",
    "decide_function_loop_action",
]
