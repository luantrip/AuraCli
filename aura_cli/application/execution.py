"""Canonical, presentation-neutral ledger for one conversational turn."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4


class OperationStatus(str, Enum):
    PLANNED = "planned"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TurnPhase(str, Enum):
    THINKING = "thinking"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    RESPONDING = "responding"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


_SENSITIVE_PARTS = ("key", "token", "secret", "password", "authorization")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def sanitize_arguments(arguments: Mapping[str, Any]) -> dict[str, Any]:
    """Redact credentials recursively before they enter the ledger."""
    sanitized: dict[str, Any] = {}
    for key, value in arguments.items():
        if any(part in key.casefold() for part in _SENSITIVE_PARTS):
            sanitized[key] = "[REDACTED]"
        elif isinstance(value, Mapping):
            sanitized[key] = sanitize_arguments(value)
        elif isinstance(value, (list, tuple)):
            sanitized[key] = [
                sanitize_arguments(item) if isinstance(item, Mapping) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    return sanitized


@dataclass
class OperationEvidence:
    exit_code: int | None = None
    paths: list[str] = field(default_factory=list)
    existing_paths: list[str] = field(default_factory=list)
    existed_before: bool | None = None
    repository: str | None = None
    branch: str | None = None
    commit: str | None = None


@dataclass
class OperationRecord:
    operation_id: str
    tool_call_id: str
    category: str
    label: str
    target: str | None
    arguments_sanitized: dict[str, Any]
    status: OperationStatus = OperationStatus.PLANNED
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration: float | None = None
    result_summary: str | None = None
    output_reference: str | None = None
    evidence: OperationEvidence = field(default_factory=OperationEvidence)


@dataclass
class DelegationRecord:
    task_id: str
    worker: str
    status: str
    thread_name: str | None = None
    accepted_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    fallback_reason: str | None = None


@dataclass
class LLMCallRecord:
    llm_call_id: str
    provider: str
    model: str
    attempt: int
    timeout: float
    status: str = "running"
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    duration: float | None = None
    fallback: bool = False
    error: str | None = None


@dataclass
class TurnExecution:
    session_id: str
    turn_id: str = field(default_factory=lambda: uuid4().hex)
    phase: TurnPhase = TurnPhase.THINKING
    started_at: datetime = field(default_factory=utc_now)
    finished_at: datetime | None = None
    operations: list[OperationRecord] = field(default_factory=list)
    delegations: list[Any] = field(default_factory=list)
    llm_calls: list[LLMCallRecord] = field(default_factory=list)
    token_usage: dict[str, int] = field(default_factory=dict)
    completion_evidence: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a schema-neutral representation suitable for persistence."""
        return {
            "session_id": self.session_id,
            "turn_id": self.turn_id,
            "phase": self.phase.value,
            "started_at": self.started_at.isoformat(),
            "finished_at": _datetime_text(self.finished_at),
            "operations": [_operation_to_dict(item) for item in self.operations],
            "delegations": [_delegation_to_dict(item) for item in self.delegations],
            "llm_calls": [_llm_call_to_dict(item) for item in self.llm_calls],
            "token_usage": dict(self.token_usage),
            "completion_evidence": list(self.completion_evidence),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> TurnExecution:
        """Restore a persisted turn without inferring facts from display text."""
        turn = cls(
            session_id=str(value["session_id"]),
            turn_id=str(value["turn_id"]),
            phase=TurnPhase(str(value.get("phase", TurnPhase.THINKING.value))),
            started_at=_parse_datetime(value.get("started_at")) or utc_now(),
            finished_at=_parse_datetime(value.get("finished_at")),
            token_usage={
                str(key): int(amount)
                for key, amount in dict(value.get("token_usage", {})).items()
            },
            completion_evidence=[
                str(item) for item in value.get("completion_evidence", [])
            ],
        )
        turn.operations = [
            _operation_from_dict(item) for item in value.get("operations", [])
        ]
        turn.delegations = [
            _delegation_from_dict(item) for item in value.get("delegations", [])
        ]
        turn.llm_calls = [
            LLMCallRecord(**_llm_call_from_dict(item))
            for item in value.get("llm_calls", [])
        ]
        return turn

    @property
    def files_read(self) -> list[str]:
        return _unique_targets(self.operations, {"read_file"})

    @property
    def files_created(self) -> list[str]:
        return _unique_evidence_paths(
            self.operations, {"write_file"}, existed_before=False
        )

    @property
    def files_edited(self) -> list[str]:
        explicit_edits = _unique_evidence_paths(
            self.operations, {"edit_file", "replace_in_file"}
        )
        overwritten = _unique_evidence_paths(
            self.operations, {"write_file"}, existed_before=True
        )
        return list(dict.fromkeys([*explicit_edits, *overwritten]))

    @property
    def failures(self) -> list[OperationRecord]:
        return [
            item for item in self.operations if item.status is OperationStatus.FAILED
        ]

    def plan_operation(
        self, tool_call_id: str, name: str, arguments: Mapping[str, Any]
    ) -> OperationRecord:
        if any(item.tool_call_id == tool_call_id for item in self.operations):
            raise ValueError(f"duplicate tool_call_id: {tool_call_id}")
        target = next(
            (
                str(arguments[key])
                for key in ("path", "file_path", "command", "task")
                if arguments.get(key) is not None
            ),
            None,
        )
        record = OperationRecord(
            operation_id=uuid4().hex,
            tool_call_id=tool_call_id,
            category=_category(name),
            label=name,
            target=target,
            arguments_sanitized=sanitize_arguments(arguments),
        )
        if record.category == "file_mutation" and target:
            record.evidence.paths = [target]
            record.evidence.existed_before = Path(target).exists()
        self.operations.append(record)
        self.phase = TurnPhase.EXECUTING
        return record

    def operation(self, tool_call_id: str) -> OperationRecord:
        return next(
            item for item in self.operations if item.tool_call_id == tool_call_id
        )

    def start_operation(self, tool_call_id: str) -> None:
        record = self.operation(tool_call_id)
        record.status = OperationStatus.RUNNING
        record.started_at = utc_now()

    def finish_operation(
        self,
        tool_call_id: str,
        result: Any,
        duration: float,
        *,
        blocked: bool = False,
        evidence_update: Mapping[str, Any] | None = None,
    ) -> None:
        record = self.operation(tool_call_id)
        record.finished_at = utc_now()
        record.duration = duration
        record.result_summary = str(result)[:1000]
        record.status = (
            OperationStatus.CANCELLED
            if blocked
            else OperationStatus.FAILED
            if _result_failed(result)
            else OperationStatus.SUCCEEDED
        )
        record.evidence = _evidence(
            record.label,
            record.target,
            result,
            existed_before=record.evidence.existed_before,
        )
        if evidence_update:
            for key in ("repository", "branch", "commit"):
                value = evidence_update.get(key)
                if isinstance(value, str) and value:
                    setattr(record.evidence, key, value)
        if record.category == "delegation":
            task_id = getattr(result, "task_id", None)
            status = getattr(result, "status", None)
            worker = getattr(result, "agent_type", None)
            if task_id and status and worker:
                self.delegations.append(
                    DelegationRecord(
                        task_id=str(task_id),
                        worker=str(worker),
                        status="accepted" if status == "started" else str(status),
                        thread_name=getattr(result, "thread_name", None),
                    )
                )

    def fail_operation(self, tool_call_id: str, error: BaseException) -> None:
        """Close an operation that raised before producing a normal outcome."""
        record = self.operation(tool_call_id)
        record.finished_at = utc_now()
        record.duration = (
            (record.finished_at - record.started_at).total_seconds()
            if record.started_at
            else 0.0
        )
        record.result_summary = f"{type(error).__name__}: {error}"[:1000]
        record.status = OperationStatus.FAILED


def _category(name: str) -> str:
    if name in {"write_file", "edit_file", "replace_in_file"}:
        return "file_mutation"
    if name in {"run_shell_command", "execute_command"}:
        return "shell"
    if name.startswith("delegate_to_"):
        return "delegation"
    if name.startswith("git_"):
        return "git"
    if name in {"read_file", "list_directory", "tree_view"}:
        return "read"
    return "tool"


def _datetime_text(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_datetime(value: Any) -> datetime | None:
    return datetime.fromisoformat(str(value)) if value else None


def _operation_to_dict(record: OperationRecord) -> dict[str, Any]:
    return {
        "operation_id": record.operation_id,
        "tool_call_id": record.tool_call_id,
        "category": record.category,
        "label": record.label,
        "target": record.target,
        "arguments_sanitized": record.arguments_sanitized,
        "status": record.status.value,
        "started_at": _datetime_text(record.started_at),
        "finished_at": _datetime_text(record.finished_at),
        "duration": record.duration,
        "result_summary": record.result_summary,
        "output_reference": record.output_reference,
        "evidence": {
            name: getattr(record.evidence, name)
            for name in OperationEvidence.__dataclass_fields__
        },
    }


def _operation_from_dict(value: Mapping[str, Any]) -> OperationRecord:
    evidence = value.get("evidence", {})
    return OperationRecord(
        operation_id=str(value["operation_id"]),
        tool_call_id=str(value["tool_call_id"]),
        category=str(value["category"]),
        label=str(value["label"]),
        target=str(value["target"]) if value.get("target") is not None else None,
        arguments_sanitized=dict(value.get("arguments_sanitized", {})),
        status=OperationStatus(str(value.get("status", OperationStatus.PLANNED.value))),
        started_at=_parse_datetime(value.get("started_at")),
        finished_at=_parse_datetime(value.get("finished_at")),
        duration=value.get("duration"),
        result_summary=value.get("result_summary"),
        output_reference=value.get("output_reference"),
        evidence=OperationEvidence(**dict(evidence)),
    )


def _delegation_to_dict(record: Any) -> dict[str, Any]:
    if isinstance(record, DelegationRecord):
        return {
            "task_id": record.task_id,
            "worker": record.worker,
            "status": record.status,
            "thread_name": record.thread_name,
            "accepted_at": record.accepted_at.isoformat(),
            "finished_at": _datetime_text(record.finished_at),
            "fallback_reason": record.fallback_reason,
        }
    return {"value": str(record)}


def _delegation_from_dict(value: Mapping[str, Any]) -> DelegationRecord:
    return DelegationRecord(
        task_id=str(value.get("task_id", "")),
        worker=str(value.get("worker", "")),
        status=str(value.get("status", "unknown")),
        thread_name=value.get("thread_name"),
        accepted_at=_parse_datetime(value.get("accepted_at")) or utc_now(),
        finished_at=_parse_datetime(value.get("finished_at")),
        fallback_reason=value.get("fallback_reason"),
    )


def _llm_call_to_dict(record: LLMCallRecord) -> dict[str, Any]:
    return {
        **record.__dict__,
        "started_at": record.started_at.isoformat(),
        "finished_at": _datetime_text(record.finished_at),
    }


def _llm_call_from_dict(value: Mapping[str, Any]) -> dict[str, Any]:
    restored = dict(value)
    restored["started_at"] = _parse_datetime(value.get("started_at")) or utc_now()
    restored["finished_at"] = _parse_datetime(value.get("finished_at"))
    return restored


def _result_failed(result: Any) -> bool:
    attribute_exit_code = getattr(result, "exit_code", None)
    if isinstance(attribute_exit_code, int):
        return attribute_exit_code != 0
    if isinstance(result, Mapping):
        if result.get("ok") is False:
            return True
        exit_code = result.get("exit_code")
        return isinstance(exit_code, int) and exit_code != 0
    text = str(result).casefold()
    return any(marker in text for marker in ("erro:", "error:", "falhou", "failed"))


def _evidence(
    name: str,
    target: str | None,
    result: Any,
    *,
    existed_before: bool | None,
) -> OperationEvidence:
    exit_code = (
        result.get("exit_code")
        if isinstance(result, Mapping)
        else getattr(result, "exit_code", None)
    )
    paths = (
        [target]
        if target and name in {"write_file", "edit_file", "replace_in_file"}
        else []
    )
    return OperationEvidence(
        exit_code=exit_code if isinstance(exit_code, int) else None,
        paths=paths,
        existing_paths=[path for path in paths if Path(path).exists()],
        existed_before=existed_before,
    )


def _unique_targets(operations: list[OperationRecord], labels: set[str]) -> list[str]:
    return list(
        dict.fromkeys(
            item.target
            for item in operations
            if item.label in labels and item.target is not None
        )
    )


def _unique_evidence_paths(
    operations: list[OperationRecord],
    labels: set[str],
    *,
    existed_before: bool | None = None,
) -> list[str]:
    return list(
        dict.fromkeys(
            path
            for item in operations
            if item.label in labels
            and item.status is OperationStatus.SUCCEEDED
            and (
                existed_before is None or item.evidence.existed_before is existed_before
            )
            for path in item.evidence.existing_paths
        )
    )


__all__ = [
    "DelegationRecord",
    "OperationEvidence",
    "OperationRecord",
    "OperationStatus",
    "TurnExecution",
    "TurnPhase",
    "sanitize_arguments",
]
