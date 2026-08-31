"""Security pattern scanner using regex and ast analysis."""

import ast
import re
from typing import Dict, List

# Patterns for hardcoded secrets (assignment with literal string)
_SECRET_RE = re.compile(
    r"""(?:password|passwd|secret|api_key|apikey|token|auth_token)"""
    r"""\s*=\s*['"][^'"]+['"]""",
    re.IGNORECASE,
)

# SQL injection: f-string or .format() with SQL keywords
_SQL_FSTRING_RE = re.compile(
    r"""f['"].*(?:SELECT|INSERT|UPDATE|DELETE|DROP)\b.*\{""",
    re.IGNORECASE,
)

# Insecure HTTP URLs
_HTTP_RE = re.compile(r"""https?://""")
_INSECURE_HTTP_RE = re.compile(r"""http://(?!localhost|127\.0\.0\.1|0\.0\.0\.0)""")


def scan_security(source: str, filepath: str = "") -> List[Dict]:
    """Scan source code for security anti-patterns.

    Args:
        source: Python source code string.
        filepath: Optional filepath for context.

    Returns:
        List of finding dicts with type, rule, line, message, severity.
    """
    findings: List[Dict] = []
    lines = source.splitlines()

    # Line-based regex checks
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        if _SECRET_RE.search(line):
            findings.append(
                {
                    "type": "security",
                    "rule": "hardcoded-secret",
                    "line": i,
                    "message": "Possible hardcoded secret detected",
                    "severity": "high",
                }
            )

        if _SQL_FSTRING_RE.search(line):
            findings.append(
                {
                    "type": "security",
                    "rule": "sql-injection",
                    "line": i,
                    "message": "Possible SQL injection via string formatting",
                    "severity": "critical",
                }
            )

        if _INSECURE_HTTP_RE.search(line):
            findings.append(
                {
                    "type": "security",
                    "rule": "insecure-http",
                    "line": i,
                    "message": "Insecure HTTP URL (use HTTPS)",
                    "severity": "medium",
                }
            )

    # AST-based checks
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return findings

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        func_name = _get_call_name(node)

        # Unsafe eval/exec/compile
        if (
            func_name in ("eval", "exec", "compile")
            and node.args
            and not isinstance(node.args[0], ast.Constant)
        ):
            findings.append(
                {
                    "type": "security",
                    "rule": "unsafe-eval",
                    "line": node.lineno,
                    "message": f"Unsafe use of {func_name}() with non-literal argument",
                    "severity": "critical",
                }
            )

        # subprocess with shell=True
        if func_name in ("subprocess.run", "subprocess.call", "subprocess.Popen"):
            for kw in node.keywords:
                if (
                    kw.arg == "shell"
                    and isinstance(kw.value, ast.Constant)
                    and kw.value.value is True
                ):
                    findings.append(
                        {
                            "type": "security",
                            "rule": "shell-injection",
                            "line": node.lineno,
                            "message": "subprocess called with shell=True",
                            "severity": "high",
                        }
                    )

    return findings


def _get_call_name(node: ast.Call) -> str:
    """Extract dotted call name from a Call node."""
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return f"{node.func.value.id}.{node.func.attr}"
    return ""
