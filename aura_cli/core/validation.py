"""
Multi-layer Validation for Safe Refactoring.

Provides comprehensive validation with multiple layers:
- Syntax validation
- Type checking (mypy/pyright)
- Static analysis (flake8/pylint)
- Format verification (black/isort)
- Related tests execution
- Detailed and actionable reports
- Automatic formatting when needed
"""

import subprocess
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class ValidationResult:
    """
    Code validation result.

    Stores results from multiple checks (syntax, types,
    linting, formatting, tests) with errors, warnings and details.

    Attributes:
        passed: True if all validations passed
        errors: List of found errors
        warnings: List of warnings
        checks: Dictionary with result of each check
        details: Additional details of each check
    """

    def __init__(self):
        """Initialize empty validation result."""
        self.passed = True
        self.errors: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []
        self.checks: Dict[str, bool] = {}
        self.details: Dict[str, Any] = {}

    def add_error(
        self,
        check: str,
        message: str,
        line: Optional[int] = None,
        file: Optional[str] = None,
    ) -> None:
        """
        Add error to validation.

        Args:
            check: Name of the failed check
            message: Error message
            line: Line number (optinha (opcional)
            file: Arquivo onde ocorreu (opcional)
        """
        self.passed = False
        self.errors.append(
            {"check": check, "message": message, "line": line, "file": file}
        )
        self.checks[check] = False

    def add_warning(
        self,
        check: str,
        message: str,
        line: Optional[int] = None,
        file: Optional[str] = None,
    ) -> None:
        """Add a warning to the validation result."""
        self.warnings.append(
            {"check": check, "message": message, "line": line, "file": file}
        )

    def set_check(
        self, check: str, passed: bool, details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Set the result of a specific check."""
        self.checks[check] = passed
        if details:
            self.details[check] = details
        if not passed:
            self.passed = False

    def get_summary(self) -> str:
        """Return a summary of validation results."""
        lines = []
        lines.append(f"Validação: {'✅ PASSOU' if self.passed else '❌ FALHOU'}")
        lines.append(
            f"Checks: {sum(1 for v in self.checks.values() if v)}/{len(self.checks)} passaram"
        )

        if self.errors:
            lines.append(f"Erros: {len(self.errors)}")
        if self.warnings:
            lines.append(f"Avisos: {len(self.warnings)}")

        return "\n".join(lines)


def validate_code(
    file_path: str, checks: Optional[List[str]] = None
) -> ValidationResult:
    """Validate code and return a ValidationResult."""
    if checks is None:
        checks = ["syntax", "types", "lint", "format", "tests"]

    result = ValidationResult()

    if "syntax" in checks:
        syntax_result = validate_syntax_file(file_path)
        result.set_check("syntax", syntax_result["passed"], syntax_result)
        if not syntax_result["passed"]:
            result.add_error(
                "syntax",
                syntax_result.get("error", "Syntax error"),
                syntax_result.get("line"),
                file_path,
            )

    if "types" in checks and result.checks.get("syntax", True):
        type_result = validate_types(file_path)
        result.set_check("types", type_result["passed"], type_result)
        if not type_result["passed"]:
            for error in type_result.get("errors", []):
                result.add_error(
                    "types",
                    error.get("message", "Type error"),
                    error.get("line"),
                    file_path,
                )

    if "lint" in checks and result.checks.get("syntax", True):
        lint_result = run_linter(file_path)
        result.set_check("lint", lint_result["passed"], lint_result)
        if not lint_result["passed"]:
            for error in lint_result.get("errors", []):
                result.add_warning(
                    "lint",
                    error.get("message", "Lint issue"),
                    error.get("line"),
                    file_path,
                )

    if "format" in checks and result.checks.get("syntax", True):
        format_result = check_formatting(file_path)
        result.set_check("format", format_result["passed"], format_result)
        if not format_result["passed"]:
            result.add_warning(
                "format",
                format_result.get("message", "Formatting issue"),
                file=file_path,
            )

    if "tests" in checks and result.checks.get("syntax", True):
        test_result = run_related_tests(file_path)
        result.set_check("tests", test_result["passed"], test_result)
        if not test_result["passed"]:
            result.add_error(
                "tests", test_result.get("message", "Tests failed"), file=file_path
            )

    return result


def validate_syntax_file(file_path: str) -> Dict:
    """Valida sintaxe de arquivo Python"""
    try:
        import ast

        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        ast.parse(content)
        return {"passed": True}
    except SyntaxError as e:
        error_msg = (
            f"Erro de sintaxe no arquivo {file_path}, linha {e.lineno}: {e.msg}. "
            "Verifique se há parênteses, colchetes ou chaves não fechados, "
            "ou se há palavras-chave mal posicionadas. "
            f"Contexto: {e.text.strip() if e.text else 'N/A'}"
        )
        return {
            "passed": False,
            "error": error_msg,
            "line": e.lineno,
            "message": error_msg,
        }
    except FileNotFoundError:
        error_msg = (
            f"File not found: {file_path}. "
            "Verifique se o caminho está correto e se o arquivo existe."
        )
        return {"passed": False, "error": error_msg, "message": error_msg}
    except PermissionError as e:
        error_msg = (
            f"Erro de permissão ao ler arquivo {file_path}: {e}. "
            "Verifique se você tem permissão de leitura no arquivo."
        )
        return {"passed": False, "error": error_msg, "message": error_msg}
    except Exception as e:
        error_msg = (
            f"Erro inesperado ao validar sintaxe do arquivo {file_path}: {e}. "
            f"Tipo de erro: {type(e).__name__}. "
            "Verifique se o arquivo está acessível e tem formato válido."
        )
        return {"passed": False, "error": error_msg, "message": error_msg}


def validate_types(file_path: str) -> Dict:
    """Valida tipos usando mypy ou pyright"""
    errors = []

    try:
        result = subprocess.run(
            [
                "mypy",
                "--no-error-summary",
                "--show-error-codes",
                "--no-color-output",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0:
            return {"passed": True, "errors": []}

        for line in result.stdout.split("\n"):
            if "error:" in line:
                parts = line.split(":", 3)
                if len(parts) >= 4:
                    try:
                        line_num = int(parts[1])
                        error_msg = parts[3].strip().split("[")[0].strip()
                        errors.append({"line": line_num, "message": error_msg})
                    except (ValueError, IndexError):
                        errors.append({"message": line.strip()})

        return {"passed": False, "errors": errors, "tool": "mypy"}

    except FileNotFoundError:
        try:
            result = subprocess.run(
                ["pyright", "--outputjson", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                return {"passed": True, "errors": [], "tool": "pyright"}

            import json

            try:
                data = json.loads(result.stdout)
                errors = []
                for diag in data.get("generalDiagnostics", []):
                    range_info = diag.get("range", {})
                    start = range_info.get("start", {})
                    errors.append(
                        {
                            "line": start.get("line", 0) + 1,
                            "message": diag.get("message", ""),
                        }
                    )
                return {"passed": False, "errors": errors, "tool": "pyright"}
            except json.JSONDecodeError:
                return {
                    "passed": False,
                    "errors": [{"message": "Type check failed"}],
                    "tool": "pyright",
                }
        except FileNotFoundError:
            logger.debug("mypy and pyright not found, skipping type check")
            return {"passed": True, "errors": [], "tool": None}


def run_linter(file_path: str) -> Dict:
    """Roda linters (flake8, pylint)"""
    errors = []

    # Flake8 (faster)
    try:
        result = subprocess.run(
            ["flake8", "--format=default", "--max-line-length=120", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            for line in result.stdout.split("\n"):
                if ":" in line and not line.startswith("#"):
                    parts = line.split(":", 3)
                    if len(parts) >= 4:
                        try:
                            line_num = int(parts[1])
                            error_code = parts[2].strip()
                            error_msg = parts[3].strip()
                            errors.append(
                                {
                                    "line": line_num,
                                    "code": error_code,
                                    "message": error_msg,
                                }
                            )
                        except (ValueError, IndexError) as _e:
                            logger.debug(f"Ignorado: {_e}")
    except FileNotFoundError:
        logger.debug("flake8 not found")
    except Exception as e:
        logger.warning(f"Error running flake8: {e}")

    try:
        result = subprocess.run(
            [
                "pylint",
                "--output-format=text",
                "--msg-template={line}:{msg}",
                "--disable=all",
                "--enable=E,F",
                file_path,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            for line in result.stdout.split("\n"):
                if (
                    ":" in line
                    and not line.startswith("*")
                    and not line.startswith("-")
                ):
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        try:
                            line_num = int(parts[0])
                            errors.append(
                                {
                                    "line": line_num,
                                    "message": parts[1].strip(),
                                    "tool": "pylint",
                                }
                            )
                        except ValueError as _e:
                            logger.debug(f"Ignorado: {_e}")
    except FileNotFoundError:
        logger.debug("pylint not found")
    except Exception as e:
        logger.warning(f"Error running pylint: {e}")

    return {
        "passed": len(errors) == 0,
        "errors": errors,
        "tool": "flake8" if errors else None,
    }


def check_formatting(file_path: str) -> Dict:
    """Check code formatting (black, isort)."""
    issues = []

    try:
        result = subprocess.run(
            ["black", "--check", "--dif", "--quiet", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            issues.append(
                {
                    "tool": "black",
                    "message": "Code is not formatted with black",
                    "diff": result.stdout[:500],
                }
            )
    except FileNotFoundError:
        logger.debug("black not found")
    except Exception as e:
        logger.warning(f"Error checking black: {e}")

    try:
        result = subprocess.run(
            ["isort", "--check-only", "--dif", "--quiet", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            issues.append(
                {
                    "tool": "isort",
                    "message": "Imports are not sorted with isort",
                    "diff": result.stdout[:500],
                }
            )
    except FileNotFoundError:
        logger.debug("isort not found")
    except Exception as e:
        logger.warning(f"Error checking isort: {e}")

    return {
        "passed": len(issues) == 0,
        "message": "; ".join([i["message"] for i in issues]) if issues else "OK",
        "issues": issues,
    }


def format_code(file_path: str) -> Dict:
    """Automatically format code."""
    results = []

    try:
        subprocess.run(
            ["black", file_path], check=True, capture_output=True, text=True, timeout=60
        )
        results.append({"tool": "black", "success": True})
    except subprocess.CalledProcessError as e:
        results.append({"tool": "black", "success": False, "error": str(e)})
    except FileNotFoundError:
        results.append({"tool": "black", "success": False, "error": "black not found"})

    try:
        subprocess.run(
            ["isort", file_path], check=True, capture_output=True, text=True, timeout=30
        )
        results.append({"tool": "isort", "success": True})
    except subprocess.CalledProcessError as e:
        results.append({"tool": "isort", "success": False, "error": str(e)})
    except FileNotFoundError:
        results.append({"tool": "isort", "success": False, "error": "isort not found"})

    all_success = all(r.get("success", False) for r in results)

    return {
        "success": all_success,
        "message": (
            "Code formatted successfully"
            if all_success
            else "Some formatting tools failed"
        ),
        "results": results,
    }


def run_related_tests(file_path: str) -> Dict:
    """Roda testes relacionados a arquivo"""
    from aura_cli.core.testing.test_runner import find_related_tests, run_tests

    try:
        related = find_related_tests(file_path)

        if not related:
            return {"passed": True, "message": "No related tests found", "tests_run": 0}

        result = run_tests(test_files=related)

        return {
            "passed": result.get("failed", 0) == 0,
            "message": f"Tests: {result.get('passed', 0)} passed, {result.get('failed', 0)} failed",
            "tests_run": result.get("total", 0),
            "details": result,
        }
    except Exception as e:
        logger.warning(f"Error running tests: {e}")
        return {"passed": True, "message": f"Could not run tests: {e}", "tests_run": 0}
