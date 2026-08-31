"""Pure construction and risk policies for multi-file edit plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Mapping
import uuid


class EditStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    DEPENDENCY_ORDER = "dependency_order"
    SAFE = "safe"


@dataclass
class EditOperation:
    id: str
    file_path: str
    old_content: str
    new_content: str
    description: str
    dependencies: list[str] = field(default_factory=list)
    priority: int = 5


@dataclass
class EditPlan:
    plan_id: str
    description: str
    strategy: EditStrategy
    operations: list[EditOperation] = field(default_factory=list)
    estimated_risk: float = 5.0
    backup_required: bool = True


def order_edit_operations(operations: Iterable[EditOperation]) -> list[EditOperation]:
    """Order operations topologically, retaining cyclic/unresolved items at the end."""
    pending = list(operations)
    in_degree = {operation.id: len(operation.dependencies) for operation in pending}
    ready = [operation for operation in pending if in_degree[operation.id] == 0]
    ordered: list[EditOperation] = []
    while ready:
        current = ready.pop(0)
        ordered.append(current)
        for operation in pending:
            if current.id in operation.dependencies:
                in_degree[operation.id] -= 1
                if in_degree[operation.id] == 0:
                    ready.append(operation)
    ordered.extend(operation for operation in pending if operation not in ordered)
    return ordered


def estimate_edit_risk(operations: Iterable[EditOperation]) -> float:
    """Estimate risk from edit volume, critical filenames and dependency depth."""
    items = list(operations)
    if not items:
        return 0.0
    risk = 2.0 + min(len(items) * 0.5, 3.0)
    critical_files = ("__init__.py", "main.py", "config.py")
    risk += sum(
        1
        for operation in items
        if any(name in operation.file_path for name in critical_files)
    )
    risk += min(max(len(operation.dependencies) for operation in items) * 0.5, 2.0)
    return min(max(risk, 0.0), 10.0)


def build_edit_plan(
    description: str,
    operations: Iterable[Mapping[str, Any]],
    strategy: EditStrategy = EditStrategy.DEPENDENCY_ORDER,
    *,
    id_factory: Callable[[], str] = lambda: str(uuid.uuid4())[:8],
) -> EditPlan:
    """Normalize operation inputs and build a deterministic edit plan."""
    normalized = [
        EditOperation(
            id=str(data.get("id") or id_factory()),
            file_path=str(data["file_path"]),
            old_content=str(data["old_content"]),
            new_content=str(data["new_content"]),
            description=str(data.get("description", "")),
            dependencies=list(data.get("dependencies", [])),
            priority=int(data.get("priority", 5)),
        )
        for data in operations
    ]
    if strategy is EditStrategy.DEPENDENCY_ORDER:
        normalized = order_edit_operations(normalized)
    risk = estimate_edit_risk(normalized)
    return EditPlan(
        plan_id=id_factory(),
        description=description,
        strategy=strategy,
        operations=normalized,
        estimated_risk=risk,
        backup_required=risk >= 5.0,
    )
