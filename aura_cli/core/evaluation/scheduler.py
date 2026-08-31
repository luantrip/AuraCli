"""Durable scheduling and resume support for evaluation runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import json
import os
from pathlib import Path
import tempfile
import threading
import time
from typing import Any
import uuid


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class RunRecord:
    run_id: str
    task_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    status: RunStatus = RunStatus.PENDING
    attempts: int = 0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    error: str | None = None
    result_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunRecord:
        copied = dict(data)
        copied["status"] = RunStatus(copied.get("status", RunStatus.PENDING))
        return cls(**copied)


class RunScheduler:
    """A lock-protected JSON-backed queue with explicit resume semantics."""

    def __init__(self, state_path: Path) -> None:
        self.state_path = Path(state_path)
        self._lock = threading.RLock()
        self._runs: dict[str, RunRecord] = {}
        self._load()

    def enqueue(self, task_id: str, payload: dict[str, Any] | None = None) -> RunRecord:
        with self._lock:
            record = RunRecord(uuid.uuid4().hex, task_id, payload or {})
            self._runs[record.run_id] = record
            self._save()
            return record

    def claim_next(self) -> RunRecord | None:
        with self._lock:
            pending = [run for run in self._runs.values() if run.status == RunStatus.PENDING]
            if not pending:
                return None
            record = min(pending, key=lambda run: (run.created_at, run.run_id))
            record.status = RunStatus.RUNNING
            record.attempts += 1
            record.updated_at = time.time()
            self._save()
            return record

    def complete(self, run_id: str, result_path: str | None = None) -> RunRecord:
        return self._transition(run_id, RunStatus.COMPLETED, result_path=result_path)

    def fail(self, run_id: str, error: str, *, retry: bool = False) -> RunRecord:
        status = RunStatus.PENDING if retry else RunStatus.FAILED
        return self._transition(run_id, status, error=error)

    def cancel(self, run_id: str) -> RunRecord:
        return self._transition(run_id, RunStatus.CANCELLED)

    def resume(self) -> list[RunRecord]:
        """Move interrupted runs back to pending and persist the recovery."""
        with self._lock:
            recovered = []
            for record in self._runs.values():
                if record.status == RunStatus.RUNNING:
                    record.status = RunStatus.PENDING
                    record.updated_at = time.time()
                    recovered.append(record)
            if recovered:
                self._save()
            return recovered

    def get(self, run_id: str) -> RunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def list(self, status: RunStatus | None = None) -> list[RunRecord]:
        with self._lock:
            records = list(self._runs.values())
            return [record for record in records if status is None or record.status == status]

    def _transition(self, run_id: str, status: RunStatus, **changes: Any) -> RunRecord:
        with self._lock:
            record = self._runs[run_id]
            record.status = status
            record.updated_at = time.time()
            for key, value in changes.items():
                setattr(record, key, value)
            self._save()
            return record

    def _load(self) -> None:
        if not self.state_path.exists():
            return
        payload = json.loads(self.state_path.read_text(encoding="utf-8"))
        self._runs = {item["run_id"]: RunRecord.from_dict(item) for item in payload.get("runs", [])}

    def _save(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps({"runs": [run.to_dict() for run in self._runs.values()]}, indent=2, sort_keys=True)
        fd, temporary = tempfile.mkstemp(prefix=".runs-", dir=self.state_path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.state_path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
