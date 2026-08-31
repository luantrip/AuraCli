"""Read-only discovery of external session artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Iterable


@dataclass(frozen=True)
class ExternalSessionCandidate:
    """A discovered external session without importing or executing it."""

    provider: str
    session_id: str
    path: Path
    name: str | None = None
    cwd: str | None = None
    model: str | None = None


class ExternalSessionDiscoveryError(ValueError):
    """Raised when a provider reference matches multiple external sessions."""


def discover_external_sessions(
    provider: str,
    *,
    roots: Iterable[Path] | None = None,
    limit: int = 200,
) -> list[ExternalSessionCandidate]:
    """Index provider artifacts using bounded, read-only filesystem scans."""
    normalized = provider.casefold()
    if normalized not in {"grok", "codex"}:
        return []
    search_roots = list(roots) if roots is not None else _default_roots(normalized)
    candidates: list[ExternalSessionCandidate] = []
    seen: set[Path] = set()
    for root in search_roots:
        if not root.is_dir() or root.is_symlink():
            continue
        paths = root.rglob("summary.json") if normalized == "grok" else root.glob("*.jsonl")
        for path in paths:
            resolved = path.resolve()
            if resolved in seen or path.is_symlink():
                continue
            seen.add(resolved)
            candidate = _candidate_from_path(normalized, path)
            if candidate:
                candidates.append(candidate)
            if len(candidates) >= limit:
                return candidates
    return candidates


def resolve_external_reference(reference: str) -> Path | None:
    """Resolve ``grok:<id>`` or ``codex:<id>`` to one unambiguous artifact."""
    if ":" not in reference:
        return None
    provider, identifier = reference.split(":", 1)
    provider = provider.casefold()
    if provider not in {"grok", "codex"} or not identifier:
        return None
    direct = Path(identifier).expanduser()
    if direct.exists():
        return direct
    matches = [
        item
        for item in discover_external_sessions(provider)
        if item.session_id == identifier or item.session_id.startswith(identifier)
    ]
    if len(matches) > 1:
        paths = ", ".join(str(item.path) for item in matches[:4])
        raise ExternalSessionDiscoveryError(
            f"Referência externa ambígua: {reference} ({paths})"
        )
    return matches[0].path if matches else None


def _default_roots(provider: str) -> list[Path]:
    home = Path.home()
    if provider == "grok":
        return [home / ".grok" / "sessions"]
    return [home / ".codex" / "sessions", home / ".codex" / "archived_sessions"]


def _candidate_from_path(provider: str, path: Path) -> ExternalSessionCandidate | None:
    if provider == "grok":
        summary = _read_json(path)
        info = summary.get("info", summary) if isinstance(summary, dict) else {}
        session_id = _string(info, "id")
        if not session_id:
            return None
        return ExternalSessionCandidate(
            provider=provider,
            session_id=session_id,
            path=path.parent,
            name=_string(summary, "generated_title", "session_summary"),
            cwd=_string(info, "cwd"),
            model=_string(summary, "current_model_id"),
        )
    session_id = _rollout_id(path)
    return ExternalSessionCandidate(provider=provider, session_id=session_id, path=path)


def _rollout_id(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines()[:50]:
            value: Any = json.loads(line)
            if isinstance(value, dict):
                for key in ("thread_id", "session_id", "sessionId"):
                    candidate = _string(value, key)
                    if candidate:
                        return candidate
                payload = value.get("payload")
                if isinstance(payload, dict):
                    candidate = _string(payload, "thread_id", "session_id")
                    if candidate:
                        return candidate
    except (OSError, json.JSONDecodeError):
        pass
    return path.stem


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _string(value: Any, *keys: str) -> str | None:
    if not isinstance(value, dict):
        return None
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


__all__ = [
    "ExternalSessionCandidate",
    "ExternalSessionDiscoveryError",
    "discover_external_sessions",
    "resolve_external_reference",
]
