"""Canonical compact grammar for codebase and external tool activity."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

_SENSITIVE_KEY = re.compile(
    r"(?:password|passphrase|token|secret|api[_-]?key|authorization|cookie|credential)",
    re.IGNORECASE,
)
_SECRET_ASSIGNMENT = re.compile(
    r"(?P<key>\b(?:password|passphrase|token|secret|api[_-]?key|authorization|cookie|credential)\b)"
    r"(?P<separator>\s*[:=]\s*|\s+)(?P<value>[^\s,;]+)",
    re.IGNORECASE,
)
_BEARER_VALUE = re.compile(r"(\bBearer\s+)[^\s,;]+", re.IGNORECASE)


class ToolFamily(str, Enum):
    READ = "read"
    SEARCH = "search"
    EDIT = "edit"
    SHELL = "shell"
    GIT = "git"
    TEST = "test"
    MCP = "mcp"
    OTHER = "other"


@dataclass(frozen=True)
class ToolActivityGrammar:
    family: ToolFamily
    verb: str
    target: str | None
    label: str
    outcome: str | None = None


def describe_tool_activity(
    name: str,
    args: Mapping[str, Any] | None = None,
    *,
    result: Any = None,
) -> ToolActivityGrammar:
    args = args or {}
    normalized = name.casefold()
    family = classify_tool(name, args)
    target = _target(family, args)
    verb = {
        ToolFamily.READ: "Ler",
        ToolFamily.SEARCH: "Buscar",
        ToolFamily.EDIT: "Editar",
        ToolFamily.SHELL: "Executar",
        ToolFamily.GIT: "Git",
        ToolFamily.TEST: "Testar",
        ToolFamily.MCP: "Consultar",
        ToolFamily.OTHER: _humanize(normalized),
    }[family]
    label = f"{verb} {target}" if target else verb
    return ToolActivityGrammar(family, verb, target, label, _outcome(family, result))


def classify_tool(name: str, args: Mapping[str, Any] | None = None) -> ToolFamily:
    normalized = name.casefold()
    command = str((args or {}).get("command") or "").casefold()
    if normalized.startswith(("mcp_", "@")) or "mcp" in normalized:
        return ToolFamily.MCP
    if normalized.startswith("git_") or command.startswith("git "):
        return ToolFamily.GIT
    if any(token in normalized for token in ("test", "pytest")) or any(
        token in command for token in ("pytest", "unittest", "npm test", "cargo test")
    ):
        return ToolFamily.TEST
    if normalized in {"run_shell_command", "execute_command", "shell"}:
        return ToolFamily.SHELL
    if any(
        token in normalized for token in ("search", "grep", "find_in", "query_code")
    ):
        return ToolFamily.SEARCH
    if any(
        token in normalized for token in ("write", "edit", "replace", "patch", "delete")
    ):
        return ToolFamily.EDIT
    if any(
        token in normalized for token in ("read", "list", "tree", "inspect", "analyze")
    ):
        return ToolFamily.READ
    return ToolFamily.OTHER


def _target(family: ToolFamily, args: Mapping[str, Any]) -> str | None:
    if family is ToolFamily.SEARCH:
        pattern = safe_preview(args.get("pattern") or args.get("query"), key="query")
        path = safe_preview(
            args.get("path") or args.get("directory") or ".", key="path"
        )
        return f"“{pattern}” em {path}" if pattern else path
    if family in {ToolFamily.SHELL, ToolFamily.TEST, ToolFamily.GIT}:
        return safe_preview(
            args.get("command") or args.get("message") or args.get("path"),
            key="command",
        )
    if family is ToolFamily.MCP:
        return safe_preview(
            args.get("operation") or args.get("resource") or args.get("server"),
            key="operation",
        )
    return safe_preview(
        args.get("path")
        or args.get("file_path")
        or args.get("directory")
        or args.get("project_path"),
        key="path",
    )


def _outcome(family: ToolFamily, result: Any) -> str | None:
    if result in (None, ""):
        return None
    if isinstance(result, Mapping):
        keys = {
            ToolFamily.SEARCH: ("matches", "files"),
            ToolFamily.EDIT: ("changed", "added", "removed"),
            ToolFamily.TEST: ("passed", "failed", "skipped"),
        }.get(family, ("count", "total"))
        parts = [f"{key}={result[key]}" for key in keys if key in result]
        if parts:
            return " · ".join(parts)
    return safe_preview(result, key="result", limit=100)


def safe_preview(value: Any, *, key: str | None = None, limit: int = 72) -> str | None:
    """Return a bounded preview with common credential values masked."""
    if value in (None, ""):
        return None
    if key and _SENSITIVE_KEY.search(key):
        return "[oculto]"
    text = " ".join(str(value).split())
    text = _BEARER_VALUE.sub(r"\1[oculto]", text)
    text = _SECRET_ASSIGNMENT.sub(r"\g<key>=[oculto]", text)
    return _short(text, limit=limit)


def _short(value: Any, *, limit: int = 72) -> str | None:
    if value in (None, ""):
        return None
    text = " ".join(str(value).split())
    return text if len(text) <= limit else f"{text[: limit - 1]}…"


def _humanize(value: str) -> str:
    return value.replace("_", " ").strip().capitalize() or "Ferramenta"


__all__ = [
    "ToolActivityGrammar",
    "ToolFamily",
    "classify_tool",
    "describe_tool_activity",
    "safe_preview",
]
