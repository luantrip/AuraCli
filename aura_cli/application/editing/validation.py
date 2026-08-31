"""Pure validation policies for proposed edit content."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from typing import Any

from .planning import EditOperation


@dataclass
class EditValidationResult:
    valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    syntax_valid: bool = True
    impact_analysis: dict[str, Any] = field(default_factory=dict)


def validate_python_syntax(code: str) -> bool:
    """Return whether a complete Python source string parses."""
    try:
        ast.parse(code)
    except SyntaxError:
        return False
    return True


def validate_edit_content(
    operation: EditOperation,
    current_content: str,
) -> EditValidationResult:
    """Validate replacement presence, resulting syntax and line impact."""
    errors: list[str] = []
    if operation.old_content not in current_content:
        errors.append(f"Content to replace not found in {operation.file_path}")
    syntax_valid = True
    if operation.file_path.endswith(".py"):
        resulting_content = current_content.replace(
            operation.old_content,
            operation.new_content,
            1,
        )
        syntax_valid = validate_python_syntax(resulting_content)
        if not syntax_valid:
            errors.append("Sintaxe Python inválida no conteúdo resultante")
    return EditValidationResult(
        valid=not errors,
        errors=errors,
        syntax_valid=syntax_valid,
        impact_analysis={
            "file": operation.file_path,
            "lines_changed": operation.new_content.count("\n")
            - operation.old_content.count("\n"),
        },
    )
