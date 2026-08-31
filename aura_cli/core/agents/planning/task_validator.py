"""Task validator for agents.

Validates tasks before execution, checking parameters, dependencies and constraints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.agents.agent_base import AgentTask
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class ValidationLevel(Enum):
    """Validation strictness level."""

    BASIC = "basic"  # Basic validation
    STRICT = "strict"  # Strict validation
    CUSTOM = "custom"  # Custom validation


@dataclass
class ValidationRule:
    """Validation rule (name, validator, error_message)."""

    name: str
    validator: Callable[[AgentTask], bool]
    error_message: str
    required: bool = True


@dataclass
class ValidationResult:
    """Validation result (valid, errors, warnings)."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskValidator:
    """Validates tasks before execution."""

    def __init__(self, level: ValidationLevel = ValidationLevel.BASIC):
        """Initialise the task validator."""
        self.level = level
        self.rules: List[ValidationRule] = []

        self._add_default_rules()

        logger.info(f"TaskValidator initialized (level: {level.value})")

    def _add_default_rules(self) -> None:
        """Add the default validation rules."""
        self.add_rule(
            ValidationRule(
                name="has_description",
                validator=lambda t: bool(t.description),
                error_message="Task must have a description",
                required=True,
            )
        )

        self.add_rule(
            ValidationRule(
                name="valid_priority",
                validator=lambda t: 1 <= t.priority <= 10,
                error_message="Prioridade deve estar entre 1 e 10",
                required=True,
            )
        )

        self.add_rule(
            ValidationRule(
                name="no_self_dependency",
                validator=lambda t: t.id not in t.dependencies,
                error_message="Task cannot depend on itself",
                required=True,
            )
        )

    def add_rule(self, rule: ValidationRule) -> None:
        """Register a validation rule."""
        self.rules.append(rule)
        logger.debug(f"Regra de validação '{rule.name}' adicionada")

    def validate(
        self, task: AgentTask, context: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """Validate a single task."""
        errors = []
        warnings = []
        metadata: dict[str, Any] = {}

        for rule in self.rules:
            try:
                if not rule.validator(task):
                    if rule.required:
                        errors.append(f"{rule.name}: {rule.error_message}")
                    else:
                        warnings.append(f"{rule.name}: {rule.error_message}")
            except Exception as e:
                error_msg = f"Error executing rule '{rule.name}': {e}"
                if rule.required:
                    errors.append(error_msg)
                else:
                    warnings.append(error_msg)
                logger.warning(error_msg, exc_info=True)

        if self.level == ValidationLevel.STRICT:
            strict_errors = self._strict_validation(task, context)
            errors.extend(strict_errors)

        if context:
            dep_errors = self._validate_dependencies(task, context)
            errors.extend(dep_errors)

        valid = len(errors) == 0

        if valid:
            logger.debug(f"Task {task.id} validated successfully")
        else:
            logger.warning(f"Task {task.id} failed validation: {len(errors)} errors")

        return ValidationResult(
            valid=valid, errors=errors, warnings=warnings, metadata=metadata
        )

    def _strict_validation(
        self, task: AgentTask, context: Optional[Dict[str, Any]]
    ) -> List[str]:
        """Apply strict additional validations."""
        errors = []

        required_params = context.get("required_params", []) if context else []
        for param in required_params:
            if param not in task.parameters:
                errors.append(f"Parâmetro obrigatório '{param}' ausente")

        return errors

    def _validate_dependencies(
        self, task: AgentTask, context: Dict[str, Any]
    ) -> List[str]:
        """Validate that task dependencies are satisfied."""
        errors = []

        available_tasks = context.get("available_tasks", [])
        available_ids = {t.id for t in available_tasks} if available_tasks else set()

        for dep_id in task.dependencies:
            if dep_id not in available_ids:
                errors.append(f"Dependência '{dep_id}' não encontrada")

        return errors

    def validate_batch(
        self, tasks: List[AgentTask], context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, ValidationResult]:
        """Validate a batch of tasks."""
        results = {}

        for task in tasks:
            results[task.id] = self.validate(task, context)

        total = len(tasks)
        valid = sum(1 for r in results.values() if r.valid)

        logger.info(f"Batch validation: {valid}/{total} valid tasks")

        return results

    def get_validation_summary(
        self, results: Dict[str, ValidationResult]
    ) -> Dict[str, Any]:
        """Return a summary of validation results."""
        total = len(results)
        valid = sum(1 for r in results.values() if r.valid)
        invalid = total - valid

        total_errors = sum(len(r.errors) for r in results.values())
        total_warnings = sum(len(r.warnings) for r in results.values())

        return {
            "total": total,
            "valid": valid,
            "invalid": invalid,
            "total_errors": total_errors,
            "total_warnings": total_warnings,
            "validation_rate": valid / total if total > 0 else 0.0,
        }
