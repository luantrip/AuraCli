"""Pure normalization helpers for external agent session formats.

External sessions are treated as historical evidence.  This module never
executes commands, tools, approvals, or provider events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class ExternalSessionData:
    """Normalized conversation and metadata extracted from an external run."""

    source_format: str
    source_session_id: str | None
    name: str
    cwd: str | None
    model: str | None
    messages: tuple[dict[str, Any], ...]
    skipped_events: int = 0
    warnings: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)


def normalize_external_records(
    records: Iterable[Mapping[str, Any]],
    *,
    source_format: str,
    metadata: Mapping[str, Any] | None = None,
) -> ExternalSessionData:
    """Normalize Grok/Codex-like records without interpreting them as actions."""
    normalized: list[dict[str, Any]] = []
    skipped = 0
    warnings: list[str] = []
    session_id = None
    cwd = None
    model = None
    name = "Imported session"

    for record in records:
        session_id = session_id or _find_string(record, "sessionId", "session_id", "thread_id")
        cwd = cwd or _find_string(record, "cwd", "current_directory", "workspace")
        model = model or _find_string(record, "model", "modelId", "model_id", "current_model_id")
        name = _first_string(record, "generated_title", "title", "session_summary") or name

        extracted = _extract_message(record)
        if extracted is None:
            if _looks_executable(record):
                skipped += 1
            continue
        role, content, message_metadata = extracted
        if not content.strip():
            continue
        normalized.append(
            {
                "role": role,
                "content": content,
                "metadata": {
                    "source": source_format,
                    "imported": True,
                    "executable": False,
                    **message_metadata,
                },
            }
        )

    if skipped:
        warnings.append(
            f"{skipped} eventos de tool/comando/aprovação foram ignorados; nenhum foi executado."
        )
    return ExternalSessionData(
        source_format=source_format,
        source_session_id=session_id,
        name=name,
        cwd=cwd,
        model=model,
        messages=tuple(_deduplicate_messages(normalized)),
        skipped_events=skipped,
        warnings=tuple(warnings),
        metadata=dict(metadata or {}),
    )


def _extract_message(record: Mapping[str, Any]) -> tuple[str, str, dict[str, Any]] | None:
    """Extract only textual user/assistant messages from known event shapes."""
    update = _mapping_at(record, "params", "update") or _mapping_at(record, "update")
    if update:
        event_type = str(update.get("sessionUpdate", ""))
        if event_type in {"agent_thought_chunk", "tool_call", "tool_result", "retry_state"}:
            return None
        content = _text_from_value(update.get("content"))
        if content:
            role = "user" if event_type.startswith("user_") else "assistant"
            return role, content, {"event": event_type}

    payload = record.get("payload")
    if isinstance(payload, Mapping):
        payload_type = str(payload.get("type", ""))
        if payload_type in {"function_call", "function_call_output", "local_shell_call", "tool_call"}:
            return None
        payload_role = _normalize_role(payload.get("role"))
        content = _text_from_value(payload.get("content")) or _text_from_value(payload.get("message"))
        if payload_role and content:
            return payload_role, content, {"event": payload_type or "payload"}

    record_role = _normalize_role(record.get("role"))
    content = _text_from_value(record.get("content"))
    if not content:
        content = _text_from_value(record.get("message"))
    if record_role and content:
        return record_role, content, {"event": str(record.get("type", "message"))}
    return None


def _normalize_role(value: Any) -> str | None:
    role = str(value or "").casefold()
    if role in {"user", "human", "prompt"}:
        return "user"
    if role in {"assistant", "agent", "model"}:
        return "assistant"
    if role == "system":
        return "system"
    return None


def _text_from_value(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        if isinstance(value.get("text"), str):
            return value["text"]
        if isinstance(value.get("message"), str):
            return value["message"]
        return _text_from_value(value.get("content"))
    if isinstance(value, list):
        return "".join(_text_from_value(item) for item in value)
    return ""


def _mapping_at(value: Mapping[str, Any], *keys: str) -> Mapping[str, Any] | None:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current if isinstance(current, Mapping) else None


def _first_string(value: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _find_string(value: Mapping[str, Any], *keys: str) -> str | None:
    direct = _first_string(value, *keys)
    if direct:
        return direct
    for nested in (value.get("params"), value.get("info"), value.get("metadata"), value.get("payload")):
        if isinstance(nested, Mapping):
            found = _find_string(nested, *keys)
            if found:
                return found
    return None


def _looks_executable(record: Mapping[str, Any]) -> bool:
    payload = record.get("payload")
    payload_values = payload.values() if isinstance(payload, Mapping) else ()
    haystack = " ".join(
        [*(str(record.get(key, "")) for key in ("type", "method", "event", "name")), *(str(value) for value in payload_values)]
    )
    return any(token in haystack.casefold() for token in ("tool", "command", "approval", "shell", "function_call"))


def _deduplicate_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for message in messages:
        if result and result[-1]["role"] == message["role"] and result[-1]["content"] == message["content"]:
            continue
        result.append(message)
    return result


__all__ = ["ExternalSessionData", "normalize_external_records"]
