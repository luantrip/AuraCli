"""Task-scoped execution capabilities for tool confirmation.

The policy is carried by a ContextVar so concurrent workers do not mutate a
shared StatsTracker value. The legacy StatsTracker flag remains a compatibility
fallback for interactive callers outside a task context.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Iterator


@dataclass
class TaskExecutionPolicy:
    """Mutable, task-local confirmation capabilities."""

    task_id: str
    auto_confirm: bool = False
    allow_dangerous: bool = False
    confirm_writes: bool = True
    fail_closed_without_adapter: bool = True
    fail_closed_policy_errors: bool = True


_current_policy: ContextVar[TaskExecutionPolicy | None] = ContextVar(
    "aura_current_execution_policy", default=None
)


def get_execution_policy() -> TaskExecutionPolicy | None:
    """Return the policy active in the current execution context."""
    return _current_policy.get()


@contextmanager
def execution_policy_context(
    policy: TaskExecutionPolicy,
) -> Iterator[TaskExecutionPolicy]:
    """Activate a task policy and restore the previous context idempotently."""
    token: Token[TaskExecutionPolicy | None] = _current_policy.set(policy)
    try:
        yield policy
    finally:
        _current_policy.reset(token)


def set_task_auto_confirm(enabled: bool) -> bool:
    """Update only the active task policy; return whether it was handled."""
    policy = _current_policy.get()
    if policy is None:
        return False
    policy.auto_confirm = enabled
    return True


def task_auto_confirm_enabled() -> bool | None:
    """Return task-local auto-confirm state, or None outside a task."""
    policy = _current_policy.get()
    return None if policy is None else policy.auto_confirm
