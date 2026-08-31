"""ADK Tool System — framework for creating and managing agent tools."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
import functools
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, TypeVar, Union

from aura_cli.application.agents import ToolResult

logger = logging.getLogger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


class ToolCategory(Enum):
    """Tool categories for organization."""

    FILE_SYSTEM = "file_system"
    CODE = "code"
    SHELL = "shell"
    WEB = "web"
    DATA = "data"
    AI = "ai"
    UTILITY = "utility"
    CUSTOM = "custom"


@dataclass
class ToolSchema:
    """Schema describing a tool's interface."""

    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    returns: str = "Any"
    category: ToolCategory = ToolCategory.UTILITY
    examples: List[str] = field(default_factory=list)

    def to_openai_schema(self) -> Dict[str, Any]:
        """Convert to OpenAI function schema format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": [
                        k
                        for k, v in self.parameters.items()
                        if v.get("required", False)
                    ],
                },
            },
        }

    def to_anthropic_schema(self) -> Dict[str, Any]:
        """Convert to Anthropic tool schema format."""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": [
                    k for k, v in self.parameters.items() if v.get("required", False)
                ],
            },
        }


class Tool:
    """
    Base class for tools.

    Tools can be created by subclassing or using the @tool decorator.

    Example (subclass):
        ```python
        class MyTool(Tool):
            name = "my_tool"
            description = "Does something useful"

            async def execute(self, param: str) -> ToolResult:
                return ToolResult.ok(f"Processed: {param}")
        ```

    Example (decorator):
        ```python
        @tool(name="my_tool", description="Does something useful")
        async def my_tool(param: str) -> str:
            return f"Processed: {param}"
        ```
    """
    name: str = "base_tool"
    description: str = "Base tool"
    category: ToolCategory = ToolCategory.UTILITY

    def __init__(self):
        """Initialize the instance."""
        self._schema: Optional[ToolSchema] = None

    @property
    def schema(self) -> ToolSchema:
        """Get the tool schema."""
        if self._schema is None:
            self._schema = self._build_schema()
        return self._schema

    def _build_schema(self) -> ToolSchema:
        """Build schema from execute method signature."""
        import typing

        sig = inspect.signature(self.execute)
        parameters = {}

        try:
            hints = typing.get_type_hints(self.execute)
        except Exception:
            hints = {}

        for param_name, param in sig.parameters.items():
            if param_name == "self":
                continue

            param_type = "string"
            annotation = hints.get(param_name, param.annotation)
            if annotation != inspect.Parameter.empty:
                origin = getattr(annotation, "__origin__", None)

                if origin is list:
                    param_type = "array"
                elif origin is dict:
                    param_type = "object"
                elif origin is Union:
                    # Optional[X] is Union[X, None]
                    args = [a for a in annotation.__args__ if a is not type(None)]
                    if args:
                        inner = args[0]
                        inner_origin = getattr(inner, "__origin__", None)
                        if inner_origin is list:
                            param_type = "array"
                        elif inner_origin is dict:
                            param_type = "object"
                        else:
                            type_map = {
                                str: "string",
                                int: "integer",
                                float: "number",
                                bool: "boolean",
                                list: "array",
                                dict: "object",
                            }
                            param_type = type_map.get(inner, "string")
                    else:
                        param_type = "string"
                else:
                    type_map = {
                        str: "string",
                        int: "integer",
                        float: "number",
                        bool: "boolean",
                        list: "array",
                        dict: "object",
                    }
                    param_type = type_map.get(annotation, "string")
            parameters[param_name] = {
                "type": param_type,
                "description": f"Parameter: {param_name}",
                "required": param.default == inspect.Parameter.empty,
            }

        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=parameters,
            category=self.category,
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute the tool. Override in subclasses."""
        raise NotImplementedError("Subclasses must implement execute()")

    async def __call__(self, **kwargs) -> ToolResult:
        """Allow calling the tool directly."""
        return await self.execute(**kwargs)

    @classmethod
    def register(cls, name: str) -> Callable[[F], F]:
        """Decorator to register a function as a tool."""

        def decorator(func: F) -> F:
            registry = get_tool_registry()
            registry.register_function(name, func)
            return func

        return decorator


def tool(
    name: Optional[str] = None,
    description: str = "",
    category: ToolCategory = ToolCategory.UTILITY,
    **kwargs,
) -> Callable[[F], F]:
    """Decorator to create a tool from a function."""

    def decorator(func: F) -> F:
        tool_name = name or func.__name__
        tool_desc = description or func.__doc__ or ""

        @functools.wraps(func)
        async def wrapper(**params) -> ToolResult:
            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(**params)
                else:
                    result = func(**params)
                return ToolResult.ok(result)
            except Exception as e:
                logger.error(f"Tool {tool_name} failed: {e}")
                return ToolResult.fail(str(e))

        wrapper._tool_name = tool_name  # type: ignore[attr-defined]
        wrapper._tool_description = tool_desc  # type: ignore[attr-defined]
        wrapper._tool_category = category  # type: ignore[attr-defined]
        wrapper._original_func = func  # type: ignore[attr-defined]

        registry = get_tool_registry()
        registry.register_function(
            tool_name, wrapper, description=tool_desc, category=category
        )

        return wrapper  # type: ignore[return-value]

    return decorator


class ToolRegistry:
    """Central registry for managing, discovering, and invoking tools."""

    def __init__(self):
        """Initialize the instance."""
        self._tools: Dict[str, Union[Tool, Callable]] = {}
        self._schemas: Dict[str, ToolSchema] = {}
        self._categories: Dict[ToolCategory, List[str]] = {
            cat: [] for cat in ToolCategory
        }

    def register(self, tool_instance: Tool) -> None:
        """Register a Tool instance."""
        self._tools[tool_instance.name] = tool_instance
        self._schemas[tool_instance.name] = tool_instance.schema
        self._categories[tool_instance.category].append(tool_instance.name)
        logger.debug(f"Registered tool: {tool_instance.name}")

    def register_function(
        self,
        name: str,
        func: Callable,
        description: str = "",
        category: ToolCategory = ToolCategory.UTILITY,
    ) -> None:
        """Register a function as a tool."""
        self._tools[name] = func

        # Build schema from function signature
        sig = inspect.signature(func)
        parameters = {}

        for param_name, param in sig.parameters.items():
            if param_name in ("self", "cls"):
                continue

            param_type = "string"
            if param.annotation != inspect.Parameter.empty:
                type_map = {
                    str: "string",
                    int: "integer",
                    float: "number",
                    bool: "boolean",
                    list: "array",
                    dict: "object",
                }
                param_type = type_map.get(param.annotation, "string")

            parameters[param_name] = {
                "type": param_type,
                "required": param.default == inspect.Parameter.empty,
            }

        self._schemas[name] = ToolSchema(
            name=name,
            description=description or func.__doc__ or "",
            parameters=parameters,
            category=category,
        )
        self._categories[category].append(name)
        logger.debug(f"Registered function tool: {name}")

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            schema = self._schemas.pop(name, None)
            if schema:
                self._categories[schema.category].remove(name)
            return True
        return False

    def get(self, name: str) -> Optional[Union[Tool, Callable]]:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_schema(self, name: str) -> Optional[ToolSchema]:
        """Get a tool's schema."""
        return self._schemas.get(name)

    async def execute(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get(name)
        if tool is None:
            return ToolResult.fail(f"Tool not found: {name}")

        try:
            if isinstance(tool, Tool):
                return await tool.execute(**kwargs)
            elif asyncio.iscoroutinefunction(tool):
                result = await tool(**kwargs)
                if isinstance(result, ToolResult):
                    return result
                return ToolResult.ok(result)
            else:
                result = tool(**kwargs)
                if isinstance(result, ToolResult):
                    return result
                return ToolResult.ok(result)
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return ToolResult.fail(str(e))

    def list_tools(self, category: Optional[ToolCategory] = None) -> List[str]:
        """List all registered tool names."""
        if category:
            return list(self._categories.get(category, []))
        return list(self._tools.keys())

    def get_all_schemas(self) -> List[ToolSchema]:
        """Get all tool schemas."""
        return list(self._schemas.values())

    def get_openai_schemas(self) -> List[Dict[str, Any]]:
        """Get all schemas in OpenAI format."""
        return [schema.to_openai_schema() for schema in self._schemas.values()]

    def get_anthropic_schemas(self) -> List[Dict[str, Any]]:
        """Get all schemas in Anthropic format."""
        return [schema.to_anthropic_schema() for schema in self._schemas.values()]

    def __len__(self) -> int:
        """Return the number of registered items."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if an item is registered."""
        return name in self._tools


# Global registry instance
_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    """Get the global tool registry."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def reset_tool_registry() -> None:
    """Reset the global tool registry (mainly for testing)."""
    global _registry
    _registry = None
