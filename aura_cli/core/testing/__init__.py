"""Testing framework for Aura CLI — discovery, execution, coverage and validation.

Re-exports: TestDiscovery (auto-discovery), find_related_tests, run_tests,
test_coverage, CoverageAnalyzer. Supports parallel execution, retry for
flaky tests, and Rich reports.
"""

from aura_cli.core.testing.coverage import CoverageAnalyzer, CoverageReport
from aura_cli.core.testing.test_discovery import TestCase, TestDiscovery
from aura_cli.core.testing.test_runner import (
    find_related_tests,
    run_tests,
    test_coverage,
    validate_tests_pass,
)
from aura_cli.core.testing.test_runner_advanced import (
    AdvancedTestRunner,
    TestResult,
    TestStatus,
)

__all__ = [
    "AdvancedTestRunner",
    "CoverageAnalyzer",
    "CoverageReport",
    "TestCase",
    "TestDiscovery",
    "TestResult",
    "TestStatus",
    "find_related_tests",
    "run_tests",
    "test_coverage",
    "validate_tests_pass",
]
