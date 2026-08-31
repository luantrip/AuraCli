"""Stable data contracts at the agent/application boundary."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


@dataclass
class AgentConfig:
    """Backend-neutral superset of agent configuration fields."""

    name: str
    role: str = ""
    description: str = ""
    system_message: str = ""
    system_prompt: str = ""
    llm_config: Dict[str, Any] = field(default_factory=dict)
    model: str = "gpt-4o"
    temperature: float = 0.7
    max_tokens: int = 4096
    capabilities: Set[AgentCapability] = field(default_factory=set)
    tools: List[str | Callable[..., Any]] = field(default_factory=list)
    memory_enabled: bool = True
    max_iterations: int = 10
    timeout_seconds: float = 300.0
    max_consecutive_auto_reply: int = 10
    human_input_mode: str = "NEVER"
    retry_on_error: bool = True
    max_retries: int = 3
    streaming: bool = True
    verbose: bool = False

    def __post_init__(self) -> None:
        if not self.description:
            self.description = self.role
        if not self.role:
            self.role = self.description
        if not self.system_prompt:
            self.system_prompt = self.system_message
        if not self.system_message:
            self.system_message = self.system_prompt
        if self.llm_config:
            self.model = self.llm_config.get("model", self.model)
            self.temperature = self.llm_config.get("temperature", self.temperature)
            self.max_tokens = self.llm_config.get("max_tokens", self.max_tokens)

    def to_dict(self) -> Dict[str, Any]:
        """Return the public ADK representation."""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "capabilities": [
                getattr(item, "value", item) for item in self.capabilities
            ],
            "tools": self.tools,
            "memory_enabled": self.memory_enabled,
            "max_iterations": self.max_iterations,
            "timeout_seconds": self.timeout_seconds,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> AgentConfig:
        """Build a config without coupling the contract to an adapter enum."""
        normalized = dict(data)
        normalized["capabilities"] = {
            item if isinstance(item, AgentCapability) else AgentCapability(item)
            for item in data.get("capabilities", [])
        }
        return cls(**normalized)


@dataclass
class AgentResponse:
    """Canonical result returned by every agent backend."""

    content: str
    success: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tokens_used: int = 0
    execution_time: float = 0.0

    @property
    def has_error(self) -> bool:
        return not self.success or self.error is not None


@dataclass
class ToolResult:
    """Canonical normalized result for tools exposed to agents."""

    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, **metadata: Any) -> ToolResult:
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def fail(cls, error: str, **metadata: Any) -> ToolResult:
        return cls(success=False, error=error, metadata=metadata)


class AgentCapability(Enum):
    """Capabilities understood consistently by every agent adapter."""

    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    CODE_REFACTORING = "code_refactoring"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    DEBUGGING = "debugging"
    ANALYSIS = "analysis"
    PLANNING = "planning"
    EXECUTION = "execution"
    WEB_SEARCH = "web_search"
    FILE_OPERATIONS = "file_operations"
    SHELL_EXECUTION = "shell_execution"
    DATA_PROCESSING = "data_processing"
    NATURAL_LANGUAGE = "natural_language"
