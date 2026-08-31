"""Cyclomatic complexity analyzer using Python's ast module."""

import ast
from typing import Dict, List


def _count_complexity(node: ast.AST) -> int:
    """Count decision points in an AST node."""
    count = 1  # base complexity
    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            count += 1
        elif isinstance(child, ast.BoolOp):
            # each `and`/`or` adds (num_values - 1) decision points
            count += len(child.values) - 1
        elif isinstance(child, (ast.ExceptHandler, ast.Assert)):
            count += 1
        elif isinstance(
            child, (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp)
        ):
            count += sum(1 for gen in child.generators for _ in gen.ifs)
        elif isinstance(child, ast.IfExp):
            count += 1
    return count


def _severity(complexity: int) -> str:
    if complexity > 10:
        return "high"
    if complexity >= 5:
        return "medium"
    return "low"


def analyze_complexity(source: str, filepath: str = "") -> List[Dict]:
    """Analyze cyclomatic complexity per function/method.

    Args:
        source: Python source code string.
        filepath: Optional filepath for context.

    Returns:
        List of finding dicts with type, function, line, complexity, severity.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    findings: List[Dict] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    c = _count_complexity(item)
                    findings.append(
                        {
                            "type": "complexity",
                            "function": f"{node.name}.{item.name}",
                            "line": item.lineno,
                            "complexity": c,
                            "severity": _severity(c),
                        }
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip methods already handled inside classes
            if any(isinstance(p, ast.ClassDef) for p in _iter_parents(tree, node)):
                continue
            c = _count_complexity(node)
            findings.append(
                {
                    "type": "complexity",
                    "function": node.name,
                    "line": node.lineno,
                    "complexity": c,
                    "severity": _severity(c),
                }
            )

    return findings


def _iter_parents(tree: ast.AST, target: ast.AST):
    """Yield parent nodes of target in the AST."""
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            if child is target:
                yield node
