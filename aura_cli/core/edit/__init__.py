"""Advanced editing system — intelligent, multi-file, safe editing.

Pipeline: EditPlanner → EditValidator → EditExecutor (with rollback) → EditHistory.
Supports single and multi-file coordinated edits with pre-execution syntax
validation and automatic revert on failure.
"""

from aura_cli.core.edit.edit_executor import EditExecutor
from aura_cli.core.edit.edit_executor import ExecutionResult as EditExecutionResult
from aura_cli.core.edit.edit_history import EditHistory, EditRecord
from aura_cli.core.edit.edit_planner import EditPlan, EditPlanner, EditStrategy
from aura_cli.core.edit.edit_validator import EditValidator
from aura_cli.core.edit.edit_validator import ValidationResult as EditValidationResult
from aura_cli.core.edit.multi_edit import EditOperation, MultiEditResult, multi_edit

__all__ = [
    "EditExecutionResult",
    "EditExecutor",
    "EditHistory",
    "EditOperation",
    "EditPlan",
    "EditPlanner",
    "EditRecord",
    "EditStrategy",
    "EditValidationResult",
    "EditValidator",
    "MultiEditResult",
    "multi_edit",
]
