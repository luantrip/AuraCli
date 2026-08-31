"""Read-only import of external agent sessions into Aura sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping
import uuid

from aura_cli.application.sessions.external import (
    ExternalSessionData,
    normalize_external_records,
)
from aura_cli.core.sessions.session_manager import Session, SessionManager


class ExternalSessionImportError(ValueError):
    """Raised when an external session cannot be safely normalized."""


@dataclass(frozen=True)
class ExternalSessionPreview:
    """Safe summary shown before importing a divergent external session."""

    source_path: Path
    source_format: str
    name: str
    message_count: int
    cwd: str | None
    model: str | None
    policy_summary: Mapping[str, Any]
    warnings: tuple[str, ...]
    divergence_reasons: tuple[str, ...]

    @property
    def requires_confirmation(self) -> bool:
        return bool(self.divergence_reasons)


def import_external_session(
    manager: SessionManager,
    source: str,
    *,
    name: str | None = None,
) -> Session:
    """Import a JSON/JSONL file or a documented session directory.

    The source is parsed as data only.  Imported tool calls, shell commands and
    approvals are recorded in the loss report and are never dispatched.
    """
    path = _resolve_source(source)
    data = _read_external(path)
    session_name = name or data.name or f"Imported {path.stem}"
    now = datetime.now().isoformat()
    session = Session(
        id=str(uuid.uuid4())[:8],
        name=f"{session_name} (imported)",
        created_at=now,
        updated_at=now,
        conversation_history=list(data.messages),
        context={
            "external_import": {
                "source_format": data.source_format,
                "source_path": str(path),
                "source_session_id": data.source_session_id,
                "skipped_events": data.skipped_events,
                "warnings": list(data.warnings),
                "metadata": dict(data.metadata),
            }
        },
        current_directory=str(manager.workspace_root or Path.cwd().resolve()),
        model=data.model or "",
        description="Imported read-only historical session",
        tags=["imported", data.source_format],
    )
    manager.save_session(session)
    return session


def inspect_external_session(source: str) -> ExternalSessionData:
    """Parse an external source without creating an Aura session."""
    path = _resolve_source(source)
    return _read_external(path)


def preview_external_session(
    source: str,
    *,
    workspace_root: Path,
    active_model: str = "",
) -> ExternalSessionPreview:
    """Build a bounded preview and identify context divergences."""
    path = _resolve_source(source)
    data = _read_external(path)
    reasons: list[str] = []
    if data.cwd and Path(data.cwd).resolve() != Path(workspace_root).resolve():
        reasons.append(f"workspace externo: {data.cwd}")
    if data.model and active_model and data.model != active_model:
        reasons.append(f"modelo externo: {data.model}")
    policy_summary = _policy_summary(data.metadata)
    if policy_summary:
        reasons.append("políticas/permissões externas não verificadas")
    return ExternalSessionPreview(
        source_path=path,
        source_format=data.source_format,
        name=data.name,
        message_count=sum(
            item.get("role") in {"user", "assistant"} for item in data.messages
        ),
        cwd=data.cwd,
        model=data.model,
        policy_summary=policy_summary,
        warnings=data.warnings,
        divergence_reasons=tuple(reasons),
    )


def _resolve_source(source: str) -> Path:
    raw = source
    for prefix in ("file:", "grok:", "codex:", "claude:", "opencode:"):
        if source.startswith(prefix):
            raw = source[len(prefix) :]
            break
    path = Path(raw).expanduser()
    if not path.exists():
        raise ExternalSessionImportError(f"Arquivo ou diretório externo não encontrado: {source}")
    if path.is_symlink():
        raise ExternalSessionImportError("Importação de sessão por link simbólico não é permitida")
    return path.resolve()


def _read_external(path: Path) -> ExternalSessionData:
    if path.is_dir():
        return _read_external_directory(path)
    if path.suffix.casefold() == ".jsonl":
        return _read_jsonl(path, source_format="jsonl")
    if path.suffix.casefold() == ".json":
        return _read_json(path)
    raise ExternalSessionImportError("Formato externo suportado: .json, .jsonl ou diretório de sessão")


def _read_external_directory(path: Path) -> ExternalSessionData:
    for filename, source_format in (
        ("updates.jsonl", "grok-acp"),
        ("chat_history.jsonl", "grok-chat-history"),
        ("rollout.jsonl", "codex-rollout"),
    ):
        candidate = path / filename
        if candidate.is_file():
            data = _read_jsonl(candidate, source_format=source_format)
            summary = path / "summary.json"
            if summary.is_file():
                data = _merge_summary(data, summary)
            return data
    for filename in ("session.json", "summary.json"):
        candidate = path / filename
        if candidate.is_file():
            return _read_json(candidate)
    raise ExternalSessionImportError(f"Nenhum arquivo de sessão reconhecido em: {path}")


def _read_jsonl(path: Path, *, source_format: str) -> ExternalSessionData:
    try:
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalSessionImportError(f"JSONL inválido: {path}: {exc}") from exc
    return normalize_external_records(records, source_format=source_format, metadata={"path": str(path)})


def _read_json(path: Path) -> ExternalSessionData:
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ExternalSessionImportError(f"JSON inválido: {path}: {exc}") from exc
    if not isinstance(raw, Mapping):
        raise ExternalSessionImportError(f"JSON de sessão deve ser um objeto: {path}")
    if isinstance(raw.get("session"), Mapping):
        raw = raw["session"]
    if isinstance(raw.get("conversation_history"), list):
        return normalize_external_records(raw["conversation_history"], source_format="aura-json", metadata={"path": str(path)})
    return normalize_external_records([raw], source_format="json", metadata={"path": str(path)})


def _merge_summary(data: ExternalSessionData, summary_path: Path) -> ExternalSessionData:
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return data
    info = summary.get("info", summary) if isinstance(summary, Mapping) else {}
    return ExternalSessionData(
        source_format=data.source_format,
        source_session_id=data.source_session_id or _string(info, "id"),
        name=data.name if data.name != "Imported session" else _string(summary, "generated_title", "session_summary") or data.name,
        cwd=data.cwd or _string(info, "cwd"),
        model=data.model or _string(summary, "current_model_id"),
        messages=data.messages,
        skipped_events=data.skipped_events,
        warnings=data.warnings,
        metadata={**data.metadata, "summary": summary},
    )


def _string(value: Any, *keys: str) -> str | None:
    if not isinstance(value, Mapping):
        return None
    for key in keys:
        candidate = value.get(key)
        if isinstance(candidate, str) and candidate:
            return candidate
    return None


def _policy_summary(metadata: Mapping[str, Any]) -> dict[str, Any]:
    """Extract policy-shaped metadata without treating it as executable policy."""
    summary = metadata.get("summary")
    if not isinstance(summary, Mapping):
        return {}
    keys = (
        "sandbox_profile",
        "approval_policy",
        "permissions",
        "permission_mode",
        "sandbox",
    )
    return {key: summary[key] for key in keys if key in summary}


__all__ = [
    "ExternalSessionImportError",
    "ExternalSessionPreview",
    "import_external_session",
    "inspect_external_session",
    "preview_external_session",
]
