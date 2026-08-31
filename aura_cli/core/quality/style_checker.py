"""Style enforcement checker using ast and text analysis."""

import ast
import re


def check_style(source: str, filepath: str = "") -> list[dict]:
    """Check Python source for style violations.

    Args:
        source: Python source code string.
        filepath: Optional filepath for context.

    Returns:
        List of finding dicts with type, rule, line, name, message, severity.
    """
    findings: list[dict] = []
    lines = source.splitlines()

    # Line length check (no AST needed)
    for i, line in enumerate(lines, 1):
        if len(line) > 120:
            findings.append(
                {
                    "type": "style",
                    "rule": "line-too-long",
                    "line": i,
                    "name": f"line:{i}",
                    "message": f"Line too long ({len(line)} > 120 chars)",
                    "severity": "low",
                }
            )

    # AST-based checks
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings

    _check_functions(tree, findings)
    _check_classes(tree, findings)
    _check_constants(tree, findings)

    return findings


_SNAKE_RE = re.compile(r"^_{0,2}[a-z][a-z0-9_]*_{0,2}$")
_PASCAL_RE = re.compile(r"^_?[A-Z][a-zA-Z0-9]*$")


def _is_dunder(name: str) -> bool:
    return name.startswith("__") and name.endswith("__")


def _check_functions(tree: ast.AST, findings: list[dict]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_dunder(node.name) and not _SNAKE_RE.match(node.name):
                findings.append(
                    {
                        "type": "style",
                        "rule": "naming-function",
                        "line": node.lineno,
                        "name": node.name,
                        "message": f"Function '{node.name}' is not snake_case",
                        "severity": "low",
                    }
                )
            # Too many arguments
            total = (
                len(node.args.args)
                + len(node.args.posonlyargs)
                + len(node.args.kwonlyargs)
            )
            if node.args.vararg:
                total += 1
            if node.args.kwarg:
                total += 1
            if total > 7:
                findings.append(
                    {
                        "type": "style",
                        "rule": "too-many-args",
                        "line": node.lineno,
                        "name": node.name,
                        "message": f"Function '{node.name}' has {total} parameters (max 7)",
                        "severity": "low",
                    }
                )


def _check_classes(tree: ast.AST, findings: list[dict]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and not _PASCAL_RE.match(node.name):
            findings.append(
                {
                    "type": "style",
                    "rule": "naming-class",
                    "line": node.lineno,
                    "name": node.name,
                    "message": f"Class '{node.name}' is not PascalCase",
                    "severity": "low",
                }
            )


def _check_constants(tree: ast.AST, findings: list[dict]) -> None:
    """Check module-level assignments that look like constants but aren't ALL_CAPS."""
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    name = target.id
                    # Skip dunder and private names, only flag names that
                    # are all-alpha-uppercase-style but fail the pattern
                    if name.startswith("_"):
                        continue
                    # Only flag if it looks like it SHOULD be a constant
                    # (all uppercase with underscores) but has lowercase
                    if re.match(r"^[A-Z]", name) and not re.match(
                        r"^[A-Z][A-Z0-9_]*$", name
                    ):
                        findings.append(
                            {
                                "type": "style",
                                "rule": "naming-constant",
                                "line": node.lineno,
                                "name": name,
                                "message": f"Module-level '{name}' looks like a constant but is not ALL_CAPS",
                                "severity": "low",
                            }
                        )
