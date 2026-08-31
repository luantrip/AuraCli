"""Ratchet against silent exception swallowing in the TUI."""

import ast
from pathlib import Path


def test_tui_has_no_pass_only_exception_handlers() -> None:
    violations = []
    root = Path("aura_cli/tui")
    for path in root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.ExceptHandler)
                and len(node.body) == 1
                and isinstance(node.body[0], ast.Pass)
            ):
                violations.append(f"{path}:{node.lineno}")
    assert violations == []
