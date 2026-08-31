"""Safe projections for tool payloads crossing into presentation surfaces."""

from __future__ import annotations

from collections.abc import Mapping
from copy import copy
from dataclasses import replace
import json
from typing import Any

from aura_cli.application.agents.events import AgiEvent, AgiEventType

REDACTED_VALUE = "[oculto]"
_MAX_ITEMS = 24
_MAX_DEPTH = 3
_TOOL_EVENT_TYPES = {AgiEventType.TOOL_EXECUTING, AgiEventType.TOOL_RESULT}
_TOOL_EVENT_TYPE_VALUES = {event_type.value for event_type in _TOOL_EVENT_TYPES}


def _event_type_value(event_type: Any) -> str:
    return str(getattr(event_type, "value", event_type))


def redact_tool_args(args: Any) -> dict[str, Any]:
    """Return a bounded shape-only projection of tool arguments.

    Tool arguments remain available to the execution pipeline, but presentation
    layers receive keys and structural hints only. Values are never copied into
    the returned mapping, including values under non-sensitive keys such as
    ``path`` or ``command``.
    """
    if not isinstance(args, Mapping):
        return {}
    return {
        str(key): _redact_value(value, depth=0)
        for key, value in list(args.items())[:_MAX_ITEMS]
    }


def safe_tool_args_json(args: Any) -> str:
    """Serialize the safe tool-argument projection for a visual surface."""
    return json.dumps(
        redact_tool_args(args),
        indent=2,
        ensure_ascii=False,
        sort_keys=True,
    )


def sanitize_event_for_presentation(event: AgiEvent) -> AgiEvent:
    """Copy an event while removing tool argument values from presentation state."""
    if (
        _event_type_value(event.type) not in _TOOL_EVENT_TYPE_VALUES
        or "tool_args" not in event.data
    ):
        return event
    data = dict(event.data)
    data["tool_args"] = redact_tool_args(data.get("tool_args"))
    return event.model_copy(update={"data": data})


def sanitize_event_dict_for_presentation(event_dict: Any) -> dict[str, Any]:
    """Return a safe, bounded event mapping for direct visual adapters."""
    if not isinstance(event_dict, Mapping):
        return {}
    projected = dict(event_dict)
    data = projected.get("data")
    if not isinstance(data, Mapping):
        return projected
    projected_data = dict(data)
    if (
        _event_type_value(projected.get("type", "")) in _TOOL_EVENT_TYPE_VALUES
        and "tool_args" in projected_data
    ):
        projected_data["tool_args"] = redact_tool_args(projected_data["tool_args"])
    projected["data"] = projected_data
    return projected


def sanitize_intervention_context(context: Any) -> Any:
    """Copy an intervention context with safe arguments for UI adapters."""
    if context is None or not hasattr(context, "tool_args"):
        return context
    safe_args = redact_tool_args(getattr(context, "tool_args", None))
    try:
        return replace(context, tool_args=safe_args)
    except (TypeError, ValueError):
        try:
            sanitized = copy(context)
            sanitized.tool_args = safe_args
            return sanitized
        except Exception:
            return context


def _redact_value(value: Any, *, depth: int) -> Any:
    if value is None:
        return None
    if depth >= _MAX_DEPTH:
        return REDACTED_VALUE
    if isinstance(value, Mapping):
        return {
            str(key): _redact_value(nested, depth=depth + 1)
            for key, nested in list(value.items())[:_MAX_ITEMS]
        }
    if isinstance(value, (list, tuple, set)):
        if not value:
            return []
        return [REDACTED_VALUE]
    return REDACTED_VALUE


__all__ = [
    "REDACTED_VALUE",
    "redact_tool_args",
    "safe_tool_args_json",
    "sanitize_event_dict_for_presentation",
    "sanitize_event_for_presentation",
    "sanitize_intervention_context",
]
