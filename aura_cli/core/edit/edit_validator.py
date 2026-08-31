"""
Edit validator for Aura CLI.

Provides validation of edits before applying,
checking syntax, dependencies and impact.
"""

from typing import Dict, List

from aura_cli.application.editing import (
    EditOperation,
    EditValidationResult,
    validate_edit_content,
    validate_python_syntax,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)
ValidationResult = EditValidationResult


class EditValidator:
    """
    Edit validator.

    Features:
    - Syntax validation
    - File verification
    - Impact analysis
    - Dependency validation
    """

    def __init__(self):
        """Initialise the edit validator."""
        logger.info("EditValidator initialized")

    def validate_operation(self, operation: EditOperation) -> ValidationResult:
        """Validate a single edit operation."""
        errors: list[str] = []
        warnings: list[str] = []

        import os

        if not os.path.exists(operation.file_path):
            errors.append(f"File not found: {operation.file_path}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        try:
            with open(operation.file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            errors.append(f"Error reading file {operation.file_path}: {e}")
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        result = validate_edit_content(operation, content)
        valid = result.valid

        if valid:
            logger.debug(f"Operação {operation.id} validada com sucesso")
        else:
            logger.warning(
                f"Operação {operation.id} falhou na validação: {len(errors)} erros"
            )

        return ValidationResult(
            valid=valid,
            errors=result.errors,
            warnings=result.warnings,
            syntax_valid=result.syntax_valid,
            impact_analysis=result.impact_analysis,
        )

    def validate_plan(
        self, operations: List[EditOperation]
    ) -> Dict[str, ValidationResult]:
        """Validate a complete edit plan."""
        results = {}

        for operation in operations:
            results[operation.id] = self.validate_operation(operation)

        total = len(operations)
        valid = sum(1 for r in results.values() if r.valid)

        logger.info(f"Plano validado: {valid}/{total} operações válidas")

        return results

    def _validate_python_syntax(self, code: str) -> bool:
        """Return True if the Python code has valid syntax."""
        return validate_python_syntax(code)
