"""Test discovery for Aura CLI.

Provides automatic test discovery and structure analysis.
"""

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class TestCase:
    """Represents a discovered test case."""

    name: str
    file_path: str
    class_name: Optional[str] = None
    line_number: int = 0
    docstring: Optional[str] = None


class TestDiscovery:
    """Automatic test discovery with filters and selection."""

    def __init__(self):
        """Initialise the test discoverer."""
        self.stats = get_stats()

        logger.info("TestDiscovery initialized")

    def discover_tests(
        self, test_path: str = ".", pattern: str = "test_*.py"
    ) -> List[TestCase]:
        """Discover all tests under a given path."""
        test_cases = []
        test_dir = Path(test_path)

        for test_file in test_dir.rglob(pattern):
            if test_file.is_file():
                cases = self._parse_test_file(test_file)
                test_cases.extend(cases)

        logger.info(f"{len(test_cases)} testes descobertos em {test_path}")

        return test_cases

    def _parse_test_file(self, file_path: Path) -> List[TestCase]:
        """Parse a test file and extract test case metadata."""
        test_cases = []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            tree = ast.parse(content, filename=str(file_path))

            current_class = None

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    current_class = node.name
                elif isinstance(node, ast.FunctionDef) and node.name.startswith(
                    "test_"
                ):
                    docstring = ast.get_docstring(node)

                    test_case = TestCase(
                        name=node.name,
                        file_path=str(file_path),
                        class_name=current_class,
                        line_number=node.lineno,
                        docstring=docstring,
                    )
                    test_cases.append(test_case)
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}", exc_info=True)

        return test_cases

    def list_tests(
        self, test_path: str = ".", pattern: str = "test_*.py"
    ) -> List[Dict[str, Any]]:
        """Return a list of discovered tests."""
        test_cases = self.discover_tests(test_path, pattern)

        return [
            {
                "name": tc.name,
                "file": tc.file_path,
                "class": tc.class_name,
                "line": tc.line_number,
            }
            for tc in test_cases
        ]

    def get_test_statistics(self, test_path: str = ".") -> Dict[str, Any]:
        """Return statistics about discovered tests."""
        test_cases = self.discover_tests(test_path)

        by_file = {}
        for tc in test_cases:
            file_path = tc.file_path
            if file_path not in by_file:
                by_file[file_path] = 0
            by_file[file_path] += 1

        return {
            "total_tests": len(test_cases),
            "total_files": len(by_file),
            "tests_per_file": by_file,
        }
