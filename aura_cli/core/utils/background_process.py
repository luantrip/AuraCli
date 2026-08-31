"""Supervision of detached background processes.

The registry keeps process evidence in memory for the lifetime of the CLI
session. It never invokes a shell parser and is deliberately injectable in
unit tests through a process factory and clock.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import signal
import subprocess
import time
from typing import Any, Callable, Iterable, Optional

IS_WINDOWS = platform.system() == "Windows"
ProcessFactory = Callable[..., Any]
Clock = Callable[[], float]


@dataclass
class BackgroundProcessRecord:
    """Public evidence for one supervised background process."""

    pid: int
    command: tuple[str, ...]
    owner_task: str | None
    started_at: float
    status: str = "running"
    finished_at: float | None = None
    exit_code: int | None = None


@dataclass
class _ManagedProcess:
    record: BackgroundProcessRecord
    process: Any


class BackgroundProcessSupervisor:
    """Register, refresh, cancel and reap detached process handles."""

    def __init__(
        self,
        *,
        process_factory: ProcessFactory = subprocess.Popen,
        clock: Clock = time.monotonic,
    ) -> None:
        self._process_factory = process_factory
        self._clock = clock
        self._processes: dict[int, _ManagedProcess] = {}

    def start(
        self,
        args: Iterable[str],
        *,
        owner_task: str | None = None,
        cwd: str | None = None,
    ) -> BackgroundProcessRecord:
        """Start an argument-vector process and register it as running."""
        command = tuple(args)
        if not command:
            raise ValueError("background command cannot be empty")

        process = self._process_factory(
            list(command),
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=cwd,
            start_new_session=True,
        )
        record = BackgroundProcessRecord(
            pid=int(process.pid),
            command=command,
            owner_task=owner_task,
            started_at=self._clock(),
        )
        self._processes[record.pid] = _ManagedProcess(record=record, process=process)
        return record

    def _refresh_managed(self, managed: _ManagedProcess) -> BackgroundProcessRecord:
        """Update a record from the process's non-blocking poll result."""
        record = managed.record
        if record.status not in {"running", "cancelling"}:
            return record

        exit_code = managed.process.poll()
        if exit_code is None:
            return record

        record.exit_code = int(exit_code)
        record.finished_at = self._clock()
        record.status = "completed" if exit_code == 0 else "failed"
        return record

    def refresh(self, pid: int | None = None) -> list[BackgroundProcessRecord]:
        """Refresh one process or all records and return public copies."""
        managed_processes = (
            [self._processes[pid]]
            if pid is not None and pid in self._processes
            else list(self._processes.values())
            if pid is None
            else []
        )
        return [self._refresh_managed(managed) for managed in managed_processes]

    def get(self, pid: int) -> BackgroundProcessRecord | None:
        """Return the refreshed record for a PID, if it is registered."""
        managed = self._processes.get(pid)
        if managed is None:
            return None
        return self._refresh_managed(managed)

    def _signal_group(self, process: Any, sig: signal.Signals) -> None:
        """Signal the isolated group, falling back to the process handle."""
        if IS_WINDOWS:
            if sig == signal.SIGKILL:
                process.kill()
            else:
                process.terminate()
            return

        try:
            group_id = os.getpgid(process.pid)
            os.killpg(group_id, sig)
        except (AttributeError, OSError, ProcessLookupError, PermissionError):
            if sig == signal.SIGKILL:
                process.kill()
            else:
                process.terminate()

    def cancel(self, pid: int) -> BackgroundProcessRecord | None:
        """Cancel a running process and ensure its handle is reaped."""
        managed = self._processes.get(pid)
        if managed is None:
            return None

        record = self._refresh_managed(managed)
        if record.status not in {"running", "cancelling"}:
            return record

        record.status = "cancelling"
        self._signal_group(managed.process, signal.SIGTERM)
        try:
            managed.process.wait(timeout=1)
        except (subprocess.TimeoutExpired, TimeoutError):
            self._signal_group(managed.process, signal.SIGKILL)
            managed.process.wait(timeout=1)

        exit_code = managed.process.poll()
        record.exit_code = int(exit_code) if exit_code is not None else -1
        record.finished_at = self._clock()
        record.status = "cancelled"
        return record

    def cancel_all(self) -> list[BackgroundProcessRecord]:
        """Cancel every registered process and return its final evidence."""
        records: list[BackgroundProcessRecord] = []
        for pid in list(self._processes):
            record = self.cancel(pid)
            if record is not None:
                records.append(record)
        return records

    def reap(self, pid: int | None = None) -> list[BackgroundProcessRecord]:
        """Remove finished records and return the evidence that was reaped."""
        records = self.refresh(pid)
        reaped: list[BackgroundProcessRecord] = []
        for record in records:
            if record.status in {"running", "cancelling"}:
                continue
            self._processes.pop(record.pid, None)
            reaped.append(record)
        return reaped

    def snapshot(self) -> list[BackgroundProcessRecord]:
        """Return refreshed records without removing them."""
        return self.refresh()


_default_supervisor: Optional[BackgroundProcessSupervisor] = None


def get_background_process_supervisor() -> BackgroundProcessSupervisor:
    """Return the session-scoped background supervisor."""
    global _default_supervisor
    if _default_supervisor is None:
        _default_supervisor = BackgroundProcessSupervisor()
    return _default_supervisor
