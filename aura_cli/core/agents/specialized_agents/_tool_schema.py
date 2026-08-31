"""
Tool schema helpers for specialized agents.

Provides a single source of truth for building the OpenAI-compatible tool
schemas that specialized agents expose to the LLM.  Schemas are derived
directly from the ServiceRegistry / TOOL_MANIFEST so they stay in sync
automatically whenever a new tool is registered.

Usage::

    from aura_cli.core.agents.specialized_agents._tool_schema import (
        schemas_for_categories,
        schemas_for_names,
    )

    class MyAgent(AgentBase):
        def _get_available_tools(self):
            return schemas_for_categories([ToolCategory.FILE_SYSTEM])
"""

from __future__ import annotations

from typing import Any, Dict, List

from aura_cli.core.logger import get_logger
from aura_cli.core.service_registry import ToolCategory, get_service_registry

logger = get_logger(__name__)

# Public helpers


def schemas_for_categories(
    categories: List[ToolCategory],
    *,
    extra_names: List[str] | None = None,
    exclude_names: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """Return OpenAI-style tool schemas for all tools in *categories*.

    Args:
        categories: ToolCategory values to include.
        extra_names: Additional tool names to add regardless of category.
        exclude_names: Tool names to suppress from the final list.

    Returns:
        List of ``{"type": "function", "function": {...}}`` dicts.
    """
    try:
        registry = get_service_registry()
    except Exception as exc:
        logger.warning(
            "ServiceRegistry unavailable — falling back to empty tool list: %s", exc
        )
        return []

    seen: set[str] = set()
    result: List[Dict[str, Any]] = []

    for cat in categories:
        for tool in registry.get_tools_by_category(cat):
            if tool.name in seen:
                continue
            seen.add(tool.name)
            schema = tool.schema
            if schema:
                result.append(schema)

    if extra_names:
        for name in extra_names:
            if name in seen:
                continue
            maybe_tool = registry.get_tool(name)
            if maybe_tool and maybe_tool.schema:
                seen.add(name)
                result.append(maybe_tool.schema)

    if exclude_names:
        excl = set(exclude_names)
        result = [s for s in result if s.get("function", {}).get("name") not in excl]

    logger.debug(
        "schemas_for_categories(%s) → %d tools",
        [c.value for c in categories],
        len(result),
    )
    return result


def schemas_for_names(names: List[str]) -> List[Dict[str, Any]]:
    """Return schemas for an explicit list of tool names.

    Tools not found in the registry are silently skipped with a debug log.
    """
    try:
        registry = get_service_registry()
    except Exception as exc:
        logger.warning("ServiceRegistry unavailable: %s", exc)
        return []

    result: List[Dict[str, Any]] = []
    for name in names:
        tool = registry.get_tool(name)
        if tool and tool.schema:
            result.append(tool.schema)
        else:
            logger.debug("Tool %r not found in ServiceRegistry — skipped", name)
    return result
