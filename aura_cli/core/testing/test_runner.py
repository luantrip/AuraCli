"""
Integrated test runner for refactoring validation.

Provides complete test integration:
- Intelligent related test detection
- Automatic test suite execution
- Code coverage analysis
- Validation before and after changes
- Support for pytest and similar frameworks
"""

import ast
from pathlib import Path
import re
import subprocess
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


def find_related_tests(file_path: str, scope: str = ".") -> List[str]:
    """Find test files related to a source file."""
    scope_path = Path(scope).resolve()
    file_path_obj = Path(file_path)

    if not file_path_obj.is_absolute():
        file_path_obj = scope_path / file_path_obj

    module_path = (
        file_path_obj.relative_to(scope_path)
        if file_path_obj.is_absolute()
        else file_path_obj
    )

    related = []

    test_files = list(scope_path.rglob("test_*.py"))
    test_files.extend(scope_path.rglob("**/tests/**/*.py"))
    test_files.extend(scope_path.rglob("**/test/**/*.py"))

    test_files = list(set(test_files))

    for test_file in test_files:
        if _should_ignore_test_file(test_file, scope_path):
            continue

        if _test_imports_module(test_file, module_path, scope_path, file_path_obj):
            normalized = str(test_file.relative_to(scope_path))
            if normalized not in related:
                related.append(normalized)

    return sorted(related)


def _should_ignore_test_file(test_file: Path, scope: Path) -> bool:
    """Return True if a test file should be skipped."""
    ignore_patterns = {
        "__pycache__",
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "build",
        "dist",
        ".pytest_cache",
        ".mypy_cache",
    }
    path_str = str(test_file)
    return any(pattern in path_str for pattern in ignore_patterns)


def _test_imports_module(
    test_file: Path, module_path: Path, scope: Path, target_file: Path
) -> bool:
    """Return True if a test file imports the given module."""
    try:
        with open(test_file, encoding="utf-8") as f:
            content = f.read()

        try:
            tree = ast.parse(content)
        except SyntaxError:
            # Cannot parse — fall back to simple search
            target_name = target_file.stem
            return (
                target_name in content or str(module_path).replace("\\", "/") in content
            )

        module_parts = (
            str(module_path)
            .replace("/", ".")
            .replace(".py", "")
            .replace("\\", ".")
            .split(".")
        )
        module_name = module_parts[-1]
        module_full = ".".join(module_parts)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if module_name in alias.name or module_full in alias.name:
                        return True

            elif isinstance(node, ast.ImportFrom) and node.module:
                if module_name in node.module or module_full in node.module:
                    return True
                if len(module_parts) > 1:
                    module_parent = ".".join(module_parts[:-1])
                    if module_parent in node.module:
                        return True

        if module_name in content or module_full in content:
            lines = content.split("\n")
            for line in lines:
                if module_name in line and not line.strip().startswith("#"):
                    return True

        return False

    except (UnicodeDecodeError, PermissionError):
        return False
    except Exception as e:
        logger.warning(f"Error checking test {test_file}: {e}")
        return False


def run_tests(
    file_path: Optional[str] = None,
    test_files: Optional[List[str]] = None,
    scope: str = ".",
) -> Dict[str, Any]:
    """Runs tests related to a modified file, or a specific list of test files, or all tests in scope.
    Auto-discovers related tests by name pattern and import analysis. Returns pass/fail counts and details.

    Args:
        file_path: Modified source file — auto-discovers related test files.
        test_files: Explicit list of test file paths to run (overrides auto-discovery).
        scope: Project root to search for tests (default: current dir).
    """
    if test_files is None:
        if file_path:
            test_files = find_related_tests(file_path, scope)
        else:
            scope_path = Path(scope).resolve()
            test_files = [
                str(f.relative_to(scope_path))
                for f in scope_path.rglob("test_*.py")
                if not _should_ignore_test_file(f, scope_path)
            ]

    if not test_files:
        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "results": [],
            "message": "No tests found",
            "success": True,
        }

    try:
        scope_path = Path(scope).resolve()
        result = subprocess.run(
            ["pytest", "-v", "--tb=short", "--no-header", *test_files],
            capture_output=True,
            text=True,
            timeout=300,
            cwd=str(scope_path),
        )

        output_lines = result.stdout.split("\n")
        passed = len(
            [
                line
                for line in output_lines
                if "PASSED" in line or "passed" in line.lower()
            ]
        )
        failed = len(
            [
                line
                for line in output_lines
                if "FAILED" in line or "failed" in line.lower()
            ]
        )

        if passed == 0 and failed == 0:
            summary_match = re.search(r"(\d+)\s+passed", result.stdout, re.IGNORECASE)
            if summary_match:
                passed = int(summary_match.group(1))

            failed_match = re.search(r"(\d+)\s+failed", result.stdout, re.IGNORECASE)
            if failed_match:
                failed = int(failed_match.group(1))

        return {
            "passed": passed,
            "failed": failed,
            "total": passed + failed,
            "results": output_lines[-20:],  # Last 20 lines
            "exit_code": result.returncode,
            "success": result.returncode == 0,
            "full_output": (
                result.stdout
                if len(result.stdout) < 5000
                else result.stdout[:5000] + "..."
            ),
        }

    except subprocess.TimeoutExpired:
        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "results": [],
            "message": "Test execution timeout (5 minutes)",
            "success": False,
        }
    except FileNotFoundError:
        logger.warning("pytest not found")
        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "results": [],
            "message": "pytest not found",
            "success": False,
        }
    except Exception as e:
        logger.error(f"Error running tests: {e}", exc_info=True)
        return {
            "passed": 0,
            "failed": 0,
            "total": 0,
            "results": [],
            "message": f"Error running tests: {e}",
            "success": False,
        }


def test_coverage(file_path: Optional[str] = None, scope: str = ".") -> float:
    """Run tests and return coverage metrics."""
    try:
        scope_path = Path(scope).resolve()
        cmd = ["pytest", "--cov", "--cov-report=term", "--cov-report="]

        if file_path:
            cmd.extend(["--cov", file_path])
            test_files = find_related_tests(file_path, scope)
            if test_files:
                cmd.extend(test_files)
        else:
            cmd.append("--cov=.")

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300, cwd=str(scope_path)
        )

        match = re.search(r"TOTAL\s+\d+\s+\d+\s+(\d+)%", result.stdout)
        if match:
            return float(match.group(1))

        match = re.search(r"(\d+(?:\.\d+)?)%", result.stdout)
        if match:
            return float(match.group(1))

        return 0.0

    except FileNotFoundError:
        logger.warning("pytest-cov not found")
        return 0.0
    except Exception as e:
        logger.warning(f"Error checking coverage: {e}")
        return 0.0


def validate_tests_pass(file_path: str, scope: str = ".") -> bool:
    """Validate that all tests pass and return a report."""
    related = find_related_tests(file_path, scope)

    if not related:
        logger.info(f"Nenhum teste relacionado encontrado para {file_path}")
        return True  # No tests = assume OK

    results = run_tests(test_files=related, scope=scope)
    passed = results.get("failed", 0) == 0

    if not passed:
        logger.warning(
            f"Testes falharam para {file_path}: {results.get('message', 'Unknown error')}"
        )

    return passed
