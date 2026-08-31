"""Policies and handoff contracts for work delegated from a conversation."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


def get_supervisor_state(
    *, status: str, alive: bool, fallback_reason: str | None
) -> str:
    """Normalize worker observations into a supervision state."""
    normalized_status = str(status or "unknown").casefold()
    normalized_reason = str(fallback_reason or "").casefold()
    if normalized_status in {"completed", "success", "done"}:
        return "completed"
    if normalized_reason == "human_approval_required":
        return "awaiting_human"
    if normalized_status in {"running", "queued", "started"} or alive:
        return "in_progress"
    if normalized_status in {"blocked", "waiting"}:
        return "returned_to_chat"
    if normalized_status == "error" or normalized_reason:
        return "returned_to_chat"
    return "delegated"


def _recent_chat_excerpt(history: list[dict[str, Any]]) -> str:
    recent: list[str] = []
    for message in reversed(history):
        role = message.get("role")
        if role not in {"user", "assistant"}:
            continue
        content = " ".join(str(message.get("content", "")).split())
        if content:
            recent.append(f"{role}: {content[:220]}")
        if len(recent) >= 6:
            break
    return "\n".join(reversed(recent))


def build_delegate_handoff(
    primary_request: str,
    *,
    agent_label: str,
    conversation_history: list[dict[str, Any]],
    project_root: Path,
    final_model: str,
    constitution: str | None,
    handoff_context: str = "",
    mode: str | None = None,
) -> str:
    """Build a compact, self-contained handoff for a delegated worker."""
    request = (primary_request or "").strip()
    context = handoff_context.strip() or _recent_chat_excerpt(conversation_history)
    lines = [
        "[CHAT DELEGATION HANDOFF]",
        f"Agent target: {agent_label}",
        f"Primary request: {request or 'Explorar o diretório atual e reportar contexto relevante.'}",
        f"Project root: {project_root}",
        f"Current chat model: {final_model}",
        f"Constitution active: {'yes' if bool(constitution) else 'no'}",
    ]
    if mode:
        lines.append(f"Requested mode: {mode}")
    lines.extend(
        [
            "Recent chat context:",
            (context or "Sem contexto adicional.")[:1400],
            "Instructions:",
            "- Treat the primary request as the source of truth.",
            "- Use the chat context only as supporting context.",
            "- You do not have the full chat history; avoid assumptions beyond this handoff.",
            "[/CHAT DELEGATION HANDOFF]",
        ]
    )
    return "\n".join(lines)


def build_delegate_payload(
    primary_request: str,
    *,
    agent_label: str,
    conversation_history: list[dict[str, Any]],
    project_root: Path,
    final_model: str,
    constitution: str | None,
    handoff_context: str = "",
    mode: str | None = None,
) -> dict[str, Any]:
    """Build structured metadata persisted with a delegated task."""
    return {
        "source": "general_chat",
        "agent_label": agent_label,
        "primary_request": (primary_request or "").strip(),
        "supporting_context": (handoff_context or "").strip(),
        "recent_chat_excerpt": _recent_chat_excerpt(conversation_history),
        "project_root": str(project_root),
        "current_chat_model": final_model,
        "constitution_active": bool(constitution),
        "delegation_mode": mode,
    }


@dataclass(frozen=True)
class DelegationPlan:
    """Prepared input for a concrete worker factory."""

    agent_type: str
    agent_label: str
    request: str
    mode: str | None
    handoff: str
    payload: dict[str, Any]


class DelegationLaunchStatus(Enum):
    BUSY = "busy"
    MISSING_CREDENTIALS = "missing_credentials"
    STARTED = "started"
    FAILED = "failed"


@dataclass(frozen=True)
class DelegationLaunchOutcome:
    """Result of attempting to launch one delegated worker."""

    status: DelegationLaunchStatus
    agent_type: str
    request: str = ""
    mode: str | None = None
    task_id: str | None = None
    thread_name: str | None = None
    error: str | None = None


class DelegationReceipt(str):
    """String-compatible launch receipt with machine-readable lifecycle data."""

    status: str
    agent_type: str
    task_id: str | None
    thread_name: str | None
    error: str | None

    def __new__(cls, message: str, outcome: DelegationLaunchOutcome):
        instance = super().__new__(cls, message)
        instance.status = outcome.status.value
        instance.agent_type = outcome.agent_type
        instance.task_id = outcome.task_id
        instance.thread_name = outcome.thread_name
        instance.error = outcome.error
        return instance


def assess_delegation_launch(
    *,
    agent_type: str,
    request: str,
    worker_active: bool,
    has_credentials: bool | None = None,
) -> DelegationLaunchOutcome | None:
    """Return an early launch outcome, or None when a factory may be called."""
    normalized = agent_type.strip().casefold()
    if normalized not in {"agi", "ops"}:
        raise ValueError(f"unsupported delegated agent type: {agent_type!r}")
    if worker_active:
        return DelegationLaunchOutcome(DelegationLaunchStatus.BUSY, normalized, request)
    if has_credentials is False:
        return DelegationLaunchOutcome(
            DelegationLaunchStatus.MISSING_CREDENTIALS, normalized, request
        )
    return None


def format_delegation_launch_outcome(
    outcome: DelegationLaunchOutcome,
) -> DelegationReceipt:
    """Render a stable user-facing message from a launch outcome."""
    label = "Aura AGI" if outcome.agent_type == "agi" else "Aura Ops"
    if outcome.status is DelegationLaunchStatus.BUSY:
        message = (
            f"A {label} já está em execução. Para uma nova tarefa, "
            "o usuário pode reiniciar a sessão ou aguardar a conclusão da tarefa atual."
        )
        return DelegationReceipt(message, outcome)
    if outcome.status is DelegationLaunchStatus.MISSING_CREDENTIALS:
        message = (
            "Nenhuma API key configurada. Peça ao usuário para configurar com "
            f"/settings antes de delegar à {'AGI' if outcome.agent_type == 'agi' else 'Ops'}."
        )
        return DelegationReceipt(message, outcome)
    if outcome.status is DelegationLaunchStatus.FAILED:
        message = (
            f"Não foi possível iniciar a {label}: {outcome.error}. "
            f"Sugira ao usuário usar o comando /{outcome.agent_type} manualmente."
        )
        return DelegationReceipt(message, outcome)
    excerpt = outcome.request[:200]
    if len(outcome.request) > 200:
        excerpt += "..."
    mode = f" (modo {outcome.mode})" if outcome.agent_type == "ops" else ""
    noun = "objetivo" if outcome.agent_type == "agi" else "tarefa"
    message = (
        f"{label}{mode} foi acionada em background com {noun}: «{excerpt}». "
        f"task_id={outcome.task_id or 'unknown'}, "
        f"thread={outcome.thread_name or 'unknown'}. "
        "Acompanhe as atualizações no painel de status acima."
    )
    return DelegationReceipt(message, outcome)


def prepare_delegation(
    request: str,
    *,
    agent_type: str,
    conversation_history: list[dict[str, Any]],
    project_root: Path,
    final_model: str,
    constitution: str | None,
    handoff_context: str = "",
    mode: str | None = None,
) -> DelegationPlan:
    """Normalize a delegation and build both persisted and textual handoffs."""
    normalized_type = agent_type.strip().casefold()
    if normalized_type not in {"agi", "ops"}:
        raise ValueError(f"unsupported delegated agent type: {agent_type!r}")
    normalized_mode = None
    if normalized_type == "ops":
        candidate = (mode or "general").casefold()
        normalized_mode = (
            candidate if candidate in {"general", "git", "docker"} else "general"
        )
    label = "AGI" if normalized_type == "agi" else "Ops"
    payload = build_delegate_payload(
        request,
        agent_label=label,
        conversation_history=conversation_history,
        project_root=project_root,
        final_model=final_model,
        constitution=constitution,
        handoff_context=handoff_context,
        mode=normalized_mode,
    )
    handoff = build_delegate_handoff(
        request,
        agent_label=label,
        conversation_history=conversation_history,
        project_root=project_root,
        final_model=final_model,
        constitution=constitution,
        handoff_context=handoff_context,
        mode=normalized_mode,
    )
    return DelegationPlan(
        agent_type=normalized_type,
        agent_label=label,
        request=request,
        mode=normalized_mode,
        handoff=handoff,
        payload=payload,
    )


__all__ = [
    "DelegationLaunchOutcome",
    "DelegationLaunchStatus",
    "DelegationPlan",
    "DelegationReceipt",
    "assess_delegation_launch",
    "build_delegate_handoff",
    "build_delegate_payload",
    "format_delegation_launch_outcome",
    "get_supervisor_state",
    "prepare_delegation",
]
