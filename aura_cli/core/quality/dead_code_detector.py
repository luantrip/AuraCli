"""Dead code detector using Python's ast module."""

import ast


def detect_dead_code(source: str, filepath: str = "") -> list[dict]:
    """Detect dead code: unused imports, unreachable code, unused variables.

    Args:
        source: Python source code string.
        filepath: Optional filepath for context.

    Returns:
        List of finding dicts with type, rule, line, name, message, severity.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    findings: list[dict] = []
    findings.extend(_find_unused_imports(tree))
    findings.extend(_find_unreachable_code(tree))
    findings.extend(_find_unused_variables(tree))
    return findings


def _find_unused_imports(tree: ast.Module) -> list[dict]:
    """Find module-level imports never referenced as a Name node."""
    imports: dict[str, int] = {}  # name -> lineno

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                name = alias.asname if alias.asname else alias.name
                imports[name] = node.lineno

    # Collect all Name references in the entire module
    used_names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            used_names.add(node.id)
        elif isinstance(node, ast.Attribute):
            # Handle cases like `os.path` where `os` is a Name
            pass  # Name node for `os` already captured by ast.walk

    findings: list[dict] = []
    for name, lineno in imports.items():
        if name not in used_names:
            findings.append(
                {
                    "type": "dead_code",
                    "rule": "unused_import",
                    "line": lineno,
                    "name": name,
                    "message": f"Import '{name}' is never used",
                    "severity": "medium",
                }
            )
    return findings


def _find_unreachable_code(tree: ast.Module) -> list[dict]:
    """Find statements after return/raise/break/continue in the same block."""
    findings: list[dict] = []
    _TERMINATORS = (ast.Return, ast.Raise, ast.Break, ast.Continue)

    for node in ast.walk(tree):
        # Check any node that has a body (functions, if/else, loops, etc.)
        for attr in ("body", "orelse", "finalbody", "handlers"):
            block = getattr(node, attr, None)
            if not isinstance(block, list):
                continue
            found_terminator = False
            for stmt in block:
                if found_terminator:
                    findings.append(
                        {
                            "type": "dead_code",
                            "rule": "unreachable",
                            "line": stmt.lineno,
                            "name": type(stmt).__name__,
                            "message": "Unreachable code after terminator",
                            "severity": "low",
                        }
                    )
                elif isinstance(stmt, _TERMINATORS):
                    found_terminator = True

    return findings


def _find_unused_variables(tree: ast.Module) -> list[dict]:
    """Find variables assigned but never read within a function scope."""
    findings: list[dict] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue

        # Collect assigned names (simple Name targets only)
        assigned: dict[str, int] = {}  # name -> lineno
        for child in ast.walk(node):
            if isinstance(child, ast.Assign):
                for target in child.targets:
                    if isinstance(target, ast.Name):
                        assigned[target.id] = child.lineno
            elif (
                isinstance(child, ast.AnnAssign)
                and isinstance(child.target, ast.Name)
                and child.value is not None
            ):
                assigned[child.target.id] = child.lineno

        # Collect all Name loads within the function
        loaded: set[str] = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                loaded.add(child.id)

        for name, lineno in assigned.items():
            if name.startswith("_") or name == "self":
                continue
            if name not in loaded:
                findings.append(
                    {
                        "type": "dead_code",
                        "rule": "unused_variable",
                        "line": lineno,
                        "name": name,
                        "message": f"Variable '{name}' is assigned but never used",
                        "severity": "low",
                    }
                )

    return findings
