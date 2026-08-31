"""Canonical mutations and summaries for model conversation history."""

from __future__ import annotations

import json
from typing import Any, MutableSequence

# Tool result content is capped at 32 KB. This is generous enough for most
# real outputs while preventing a large read_file from filling the context window.
_MAX_TOOL_CONTENT_BYTES: int = 32_768
_TRUNCATION_NOTICE: str = (
    "\n\n[... output truncated at 32 KB — use a more specific query to see the rest ...]"
)


def _cap_tool_content(content: str) -> str:
    """Return content capped at _MAX_TOOL_CONTENT_BYTES with a truncation notice."""
    encoded = content.encode("utf-8", errors="replace")
    if len(encoded) <= _MAX_TOOL_CONTENT_BYTES:
        return content
    cutoff = _MAX_TOOL_CONTENT_BYTES - len(_TRUNCATION_NOTICE.encode("utf-8"))
    return encoded[:cutoff].decode("utf-8", errors="replace") + _TRUNCATION_NOTICE


def append_tool_interaction(
    history: MutableSequence[dict[str, Any]],
    *,
    name: str,
    arguments: dict[str, Any],
    call_id: str,
    content: str,
) -> None:
    """Append a tool call and its result atomically, capping content at 32 KB."""
    history.extend(
        [
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": name,
                            "arguments": json.dumps(arguments),
                        },
                    }
                ],
            },
            {
                "role": "tool",
                "tool_call_id": call_id,
                "name": name,
                "content": _cap_tool_content(content),
            },
        ]
    )


def summarize_tool_result(name: str, content: str) -> str | None:
    """Return a concise user-facing description of a tool result."""
    if "Erro:" in content and len(content) < 50:
        return None
    if name == "read_file":
        preview = content[:150].replace("\n", " ").strip()
        return (
            f"Li o arquivo e encontrei: {preview}{'...' if len(content) > 150 else ''}"
        )
    if name in {"write_file", "edit_file"}:
        return (
            "Arquivo modificado com sucesso"
            if any(
                word in content.lower() for word in ("sucesso", "escrito", "editado")
            )
            else None
        )
    if name == "list_directory":
        return "Listagem de diretório concluída" if "Listou" in content else None
    if name == "run_shell_command" and content:
        preview = content[:100].replace("\n", " ").strip()
        return f"Command executed: {preview}{'...' if len(content) > 100 else ''}"
    if content:
        return content if len(content) < 200 else content[:150] + "..."
    return None


def build_tool_result_response(
    history: MutableSequence[dict[str, Any]], user_request: str | None = None
) -> str:
    """Build a compact final response from recent tool results."""
    summaries = []
    for message in reversed(history[-15:]):
        if message.get("role") == "tool":
            summary = summarize_tool_result(
                message.get("name", "ferramenta"), message.get("content", "")
            )
            if summary:
                summaries.append(summary)
    if not summaries:
        if user_request:
            return (
                f"Concluí a operação solicitada: {user_request[:100]}. "
                "As ferramentas foram executadas com sucesso."
            )
        return "Operação concluída com sucesso."

    parts = []
    if user_request:
        request = user_request[:80] + ("..." if len(user_request) > 80 else "")
        parts.append(f"Concluí: {request}")
    if len(summaries) == 1:
        parts.append(summaries[0])
    elif len(summaries) <= 3:
        parts.append(" ".join(summaries))
    else:
        parts.append(f"{summaries[0]}. {summaries[1]}")
        parts.append(f"E mais {len(summaries) - 2} operações concluídas.")
    return ". ".join(parts) + "."
