"""Advanced test runner for Aura CLI.

Provides test execution with detailed reports and parallelisation.
"""

from dataclasses import dataclass
from enum import Enum
import subprocess
from typing import Any, List, Optional

from rich.console import Console
from rich.table import Table

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


class TestStatus(Enum):
    """Status de teste."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class TestResult:
    """Test result (test_name, status, duration, error_message)."""

    test_name: str
    status: TestStatus
    duration: float = 0.0
    error: Optional[str] = None
    output: Optional[str] = None


class AdvancedTestRunner:
    """Advanced test runner with parallelisation, filters and detailed reporting."""

    def __init__(self):
        """Initialise the test runner."""
        self.stats = get_stats()

        logger.info("AdvancedTestRunner initialized")

    def run_tests(
        self,
        test_path: str = ".",
        pattern: Optional[str] = None,
        parallel: bool = False,
        verbose: bool = False,
    ) -> List[TestResult]:
        """Run tests and return a detailed report."""
        try:
            from aura_cli.core.ui import display_tool_call
        except ImportError:
            display_tool_call = None  # type: ignore[assignment]

        import time

        start_time = time.time()

        if display_tool_call is not None:
            display_tool_call(
                "run_tests",
                {"test_path": test_path, "pattern": pattern, "parallel": parallel},
            )

        results: list[Any] = []

        if self._check_pytest():
            results = self._run_with_pytest(test_path, pattern, parallel, verbose)
        else:
            results = self._run_with_unittest(test_path, pattern)

        duration = time.time() - start_time

        self._display_summary(results, duration)

        self.stats.track_tool_usage("test_runner")

        return results

    def _check_pytest(self) -> bool:
        """Return True if pytest is available."""
        import shutil

        return shutil.which("pytest") is not None

    def _run_with_pytest(
        self, test_path: str, pattern: Optional[str], parallel: bool, verbose: bool
    ) -> List[TestResult]:
        """Run tests using pytest and return results."""
        import time

        cmd = ["pytest", test_path]

        if pattern:
            cmd.extend(["-k", pattern])

        if parallel:
            try:
                import pytest_xdist as _pytest_xdist

                if _pytest_xdist is not None:
                    cmd.extend(["-n", "auto"])
            except ImportError:
                logger.warning("pytest-xdist não instalado, executando sequencialmente")

        if verbose:
            cmd.append("-v")

        cmd.extend(["--tb=short", "-q"])

        try:
            start = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            duration = time.time() - start

            results = self._parse_pytest_output(result.stdout, result.stderr, duration)

            return results

        except subprocess.TimeoutExpired:
            logger.error("Timeout ao executar testes")
            return [
                TestResult(test_name="all", status=TestStatus.ERROR, error="Timeout")
            ]
        except Exception as e:
            logger.error(f"Error running pytest: {e}", exc_info=True)
            return [TestResult(test_name="all", status=TestStatus.ERROR, error=str(e))]

    def _run_with_unittest(
        self, test_path: str, pattern: Optional[str]
    ) -> List[TestResult]:
        """Run tests using unittest and return results."""
        import time
        import unittest

        loader = unittest.TestLoader()
        suite = loader.discover(test_path, pattern=pattern or "test_*.py")

        results = []

        for test in suite:
            start = time.time()
            try:
                result = unittest.TextTestRunner(verbosity=0).run(test)
                duration = time.time() - start

                # result.testsRun is an int — not iterable; record one result per suite item
                status = (
                    TestStatus.PASSED if result.wasSuccessful() else TestStatus.FAILED
                )
                results.append(
                    TestResult(
                        test_name=str(test),
                        status=status,
                        duration=duration,
                    )
                )

            except Exception as e:
                results.append(
                    TestResult(
                        test_name=str(test), status=TestStatus.ERROR, error=str(e)
                    )
                )

        return results

    def _parse_pytest_output(
        self, stdout: str, stderr: str, duration: float
    ) -> List[TestResult]:
        """Parse pytest stdout/stderr output into TestResult objects."""
        results: list[Any] = []

        lines = stdout.split("\n")

        for line in lines:
            if "PASSED" in line or "FAILED" in line or "ERROR" in line:
                parts = line.split()
                if len(parts) >= 2:
                    test_name = parts[0]
                    status_str = parts[1].lower()

                    status = TestStatus.PASSED
                    if "failed" in status_str:
                        status = TestStatus.FAILED
                    elif "error" in status_str:
                        status = TestStatus.ERROR

                    results.append(
                        TestResult(
                            test_name=test_name,
                            status=status,
                            duration=duration / max(len(results) + 1, 1),
                        )
                    )

        return results

    def _display_summary(self, results: List[TestResult], duration: float) -> None:
        """Display a test run summary to the console."""
        from aura_cli.core.ui_bridge import UIStyles

        table = Table(title="Test Results Summary", show_header=True)
        primary_style = UIStyles.PRIMARY if UIStyles is not None else "blue"
        secondary_style = (
            getattr(UIStyles, "SECONDARY", None)
            or getattr(UIStyles, "MUTED", None)
            or "dim"
        )

        table.add_column("Status", style=primary_style)
        table.add_column("Count", style=secondary_style)

        by_status: dict[str, int] = {}
        for result in results:
            result_status = result.status.value
            by_status[result_status] = by_status.get(result_status, 0) + 1

        for status in TestStatus:
            count = by_status.get(status.value, 0)
            status_style = {
                "passed": UIStyles.SUCCESS if UIStyles is not None else "green",
                "failed": UIStyles.ERROR if UIStyles is not None else "red",
                "error": UIStyles.ERROR if UIStyles is not None else "red",
                "skipped": UIStyles.WARNING if UIStyles is not None else "yellow",
            }.get(status.value, UIStyles.BODY if UIStyles is not None else "white")

            table.add_row(
                f"[{status_style}]{status.value.upper()}[/{status_style}]",
                str(count),
            )

        table.add_row("Total", str(len(results)))
        table.add_row("Duration", f"{duration:.2f}s")

        console.print(table)
