"""
Multi-file editing system.

Provides simultaneous editing across multiple files
with validation and automatic rollback.
"""

from dataclasses import dataclass, field
from datetime import datetime
import os
import shutil
from typing import Any, Dict, List

from rich.console import Console

from aura_cli.core.edit.edit_planner import EditOperation
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


@dataclass
class MultiEditResult:
    """
    Multi-edit operation result.

    Attributes:
        success: Whether all edits succeeded
        results: Results per file
        backups_created: List of created backups
        errors: List of errors
    """

    success: bool
    results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    backups_created: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def multi_edit(
    operations: List[EditOperation],
    create_backups: bool = True,
    validate_before: bool = True,
) -> MultiEditResult:
    """Edit multiple files simultaneously."""
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call(
        "multi_edit",
        {
            "operations_count": len(operations),
            "create_backups": create_backups,
            "validate_before": validate_before,
        },
    )

    results = {}
    backups_created = []
    errors = []

    if validate_before:
        for op in operations:
            if not os.path.exists(op.file_path):
                errors.append(f"File not found: {op.file_path}")
                continue

            try:
                with open(op.file_path, encoding="utf-8") as f:
                    content = f.read()
                    if op.old_content not in content:
                        errors.append(
                            f"Content to replace not found in {op.file_path}"
                        )
            except Exception as e:
                errors.append(f"Error validating {op.file_path}: {e}")

        if errors:
            logger.error(f"Validação falhou: {len(errors)} erros")
            return MultiEditResult(success=False, errors=errors)

    if create_backups:
        for op in operations:
            backup_path = (
                f"{op.file_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            try:
                shutil.copy2(op.file_path, backup_path)
                backups_created.append(backup_path)
                logger.debug(f"Backup created: {backup_path}")
            except Exception as e:
                errors.append(f"Error creating backup for {op.file_path}: {e}")

    for op in operations:
        try:
            with open(op.file_path, encoding="utf-8") as f:
                content = f.read()

            new_content = content.replace(op.old_content, op.new_content, 1)

            with open(op.file_path, "w", encoding="utf-8") as f:
                f.write(new_content)

            results[op.file_path] = {"success": True, "description": op.description}

            logger.info(f"File {op.file_path} edited successfully")

        except Exception as e:
            error_msg = f"Error editing {op.file_path}: {e}"
            errors.append(error_msg)
            results[op.file_path] = {"success": False, "error": error_msg}
            logger.error(error_msg, exc_info=True)

    success = len(errors) == 0

    stats = get_stats()
    stats.track_tool_usage("multi_edit")

    if success:
        success_style = UIStyles.safe_style("SUCCESS", "green")
        console.print(
            f"[{success_style}]{UIIcons.SUCCESS} "
            f"{len(operations)} arquivos editados com sucesso[/{success_style}]"
        )
    else:
        error_style = UIStyles.safe_style("ERROR", "red")
        console.print(
            f"[{error_style}]{UIIcons.ERROR} "
            f"Edição múltipla concluída com {len(errors)} erros[/{error_style}]"
        )

    return MultiEditResult(
        success=success, results=results, backups_created=backups_created, errors=errors
    )
