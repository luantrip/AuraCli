"""Static dependency analysis utilities for Python codebases."""

import ast
from collections import defaultdict
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from aura_cli.core.logger import get_logger

try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None


logger = get_logger(__name__)


class DependencyAnalyzer:
    """Analyzes code dependencies and import relationships.

    Builds dependency graphs and provides impact analysis for code changes.
    """

    def __init__(self, scope: str = "."):
        """Initialize the instance."""
        self.scope = Path(scope).resolve()
        self.import_graph: Any = nx.DiGraph() if HAS_NETWORKX and nx else None
        self.file_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.file_dependents: Dict[str, Set[str]] = defaultdict(set)
        self._analyzed = False
        self._file_cache: Dict[str, str] = {}
        self._python_files: Set[str] = set()

    def analyze(self) -> "DependencyAnalyzer":
        """Analyze code."""
        if self._analyzed:
            return self
        logger.info(f"Analisando dependências em {self.scope}")

        all_python_paths = []
        for root, dirs, files in os.walk(self.scope, topdown=True):
            dirs[:] = [d for d in dirs if not self._should_ignore(Path(root) / d)]
            for file in files:
                if file.endswith(".py"):
                    path = Path(root) / file
                    if not self._should_ignore(path):
                        all_python_paths.append(path)

        self._python_files = {self._normalize_path(p) for p in all_python_paths}
        logger.info(f"Found {len(all_python_paths)} Python files")

        for file_path in all_python_paths:
            self._analyze_file(file_path)

        self._build_graph()
        self._analyzed = True
        return self

    def _should_ignore(self, path: Path) -> bool:
        """Return True if the path should be excluded from analysis."""
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
            ".tox",
            ".aura",
            "coding",
            "ops_workspace",
        }
        return any(pattern in str(path) for pattern in ignore_patterns)

    def _analyze_file(self, file_path: Path):
        """Parse and analyze imports in a single file."""
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            self._file_cache[str(file_path)] = content
            tree = ast.parse(content)
            file_str = self._normalize_path(file_path)
            imports = self._extract_imports(tree, file_path)
            for imp in imports:
                if imp:
                    if HAS_NETWORKX and self.import_graph is not None:
                        self.import_graph.add_edge(file_str, imp)
                    self.file_dependencies[file_str].add(imp)
                    self.file_dependents[imp].add(file_str)
        except (SyntaxError, UnicodeDecodeError) as e:
            logger.warning(f"Error analyzing {file_path}: {e}")
        except Exception as e:
            logger.error(f"Erro inesperado ao analisar {file_path}: {e}", exc_info=True)

    def _normalize_path(self, file_path: Path) -> str:
        """Normalize a file path to a consistent format."""
        try:
            return str(file_path.relative_to(self.scope))
        except ValueError:
            return str(file_path)

    def _extract_imports(self, tree: ast.AST, file_path: Path) -> List[str]:
        """Extract all import statements from an AST."""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = self._resolve_import(alias.name)
                    if resolved:
                        imports.add(resolved)
            elif isinstance(node, ast.ImportFrom) and node.module:
                resolved = self._resolve_module_path(node.module, file_path)
                if resolved:
                    imports.add(resolved)
        return list(imports)

    def _resolve_import(self, module_name: str) -> Optional[str]:
        """Resolve an import name to a module path."""
        path_str = module_name.replace(".", "/")
        potential_paths = {f"{path_str}/__init__.py", f"{path_str}.py"}

        for path in potential_paths:
            if path in self._python_files:
                return path
        return None

    def _resolve_module_path(self, module: str, file_path: Path) -> Optional[str]:
        """Resolve a module name to a filesystem path."""
        level = 0
        while module.startswith("."):
            module = module[1:]
            level += 1

        if level > 0:
            base_path = file_path.parent
            for _ in range(level - 1):
                base_path = base_path.parent

            rel_path_str = str(base_path.relative_to(self.scope)).replace(os.sep, ".")
            if rel_path_str == ".":
                full_module_name = module
            else:
                full_module_name = f"{rel_path_str}.{module}"
        else:
            full_module_name = module

        return self._resolve_import(full_module_name)

    def _build_graph(self):
        """Build dependency graph structure."""

    def find_dependencies(self, file_path: str) -> List[str]:
        """Find all files that the given file depends on.

        Args:
            file_path: Path to file to analyze

        Returns:
            List of file paths that are dependencies
        """
        if not self._analyzed:
            self.analyze()
        file_str = self._normalize_path(Path(file_path))
        return sorted(self.file_dependencies.get(file_str, set()))

    def find_dependents(self, file_path: str) -> List[str]:
        """Find all files that depend on the given file.

        Args:
            file_path: Path to file to analyze

        Returns:
            List of file paths that depend on this file
        """
        if not self._analyzed:
            self.analyze()
        file_str = self._normalize_path(Path(file_path))
        return sorted(self.file_dependents.get(file_str, set()))

    def analyze_import_graph(self) -> Dict:
        """Analyse the full import graph."""
        if not self._analyzed:
            self.analyze()

        if HAS_NETWORKX and nx is not None and self.import_graph is not None:
            try:
                cycles = list(nx.simple_cycles(self.import_graph))
            except Exception:
                cycles = []

            in_degree = dict(self.import_graph.in_degree())
            critical_modules = sorted(
                in_degree.items(), key=lambda x: x[1], reverse=True
            )[:10]

            isolated = [
                n for n in self.import_graph.nodes() if self.import_graph.degree(n) == 0
            ]

            try:
                topological_order = list(nx.topological_sort(self.import_graph))
            except Exception:
                topological_order = []

            return {
                "nodes": len(self.import_graph.nodes()),
                "edges": len(self.import_graph.edges()),
                "cycles": cycles,
                "cycle_count": len(cycles),
                "critical_modules": critical_modules,
                "isolated_modules": isolated,
                "topological_order": (
                    topological_order[:20] if topological_order else []
                ),
                "has_networkx": True,
            }
        else:
            return {
                "nodes": 0,
                "edges": 0,
                "cycles": [],
                "cycle_count": 0,
                "critical_modules": [],
                "isolated_modules": [],
                "topological_order": [],
                "has_networkx": False,
                "warning": "networkx não instalado",
            }

    def get_impact_analysis(self, file_path: str, change_type: str = "modify") -> Dict:
        """Get impact analysis for file changes.

        Args:
            file_path: Path to file being changed
            change_type: Type of change (modify, delete, etc.)

        Returns:
            Dictionary with impact metrics and affected files
        """
        if not self._analyzed:
            self.analyze()

        file_str = self._normalize_path(Path(file_path))
        affected_files = self.find_dependents(file_str)
        dependencies = self.find_dependencies(file_str)
        related_tests = self._find_related_tests(Path(file_path))
        risk_level = self._calculate_risk(len(affected_files))

        graph_analysis = self.analyze_import_graph()
        critical_modules = graph_analysis.get("critical_modules", [])
        critical_affected = [
            f for f in affected_files if f in [m[0] for m in critical_modules]
        ]

        return {
            "file": file_path,
            "change_type": change_type,
            "affected_files": affected_files,
            "affected_count": len(affected_files),
            "critical_affected": critical_affected,
            "related_tests": related_tests,
            "test_count": len(related_tests),
            "risk_level": risk_level,
            "dependencies": dependencies,
            "dependency_count": len(dependencies),
        }

    def _find_related_tests(self, file_path: Path) -> List[str]:
        """Find related tests using os.walk heuristics."""
        file_str = self._normalize_path(file_path)
        module_name = file_path.stem
        test_patterns = {f"test_{module_name}.py"}

        related = set()
        for test_file in self._python_files:
            if test_file.startswith("tests") or "test" in test_file:
                if Path(test_file).name in test_patterns:
                    related.add(test_file)
                if file_str in self.file_dependents.get(test_file, set()):
                    related.add(test_file)
        return sorted(related)

    def _calculate_risk(self, affected_count: int) -> str:
        """Calculate the risk level based on the number of affected files."""
        if affected_count == 0:
            return "low"
        if affected_count < 10:
            return "medium"
        if affected_count < 50:
            return "high"
        return "critical"


def get_impact_analysis(
    file_path: str, change_type: str = "modify", scope: str = "."
) -> Dict[str, Any]:
    """Get impact analysis."""
    analyzer = DependencyAnalyzer(scope)
    return analyzer.get_impact_analysis(file_path, change_type)


def find_dependencies(file_path: str, scope: str = ".") -> List[str]:
    """Returns a list of files/modules that the given file directly imports or depends on.

    Args:
        file_path: Path to the file to analyze.
        scope: Root directory to resolve imports within (default: current dir).
    """
    analyzer = DependencyAnalyzer(scope)
    return analyzer.find_dependencies(file_path)


def find_dependents(file_path: str, scope: str = ".") -> List[str]:
    """Returns a list of files that import or depend on the given file.
    Use this to assess the blast radius before modifying a module.

    Args:
        file_path: Path to the file to check.
        scope: Root directory to search within (default: current dir).
    """
    analyzer = DependencyAnalyzer(scope)
    return analyzer.find_dependents(file_path)


def analyze_import_graph(scope: str = ".") -> Dict[str, Any]:
    """Analyse the full import graph."""
    analyzer = DependencyAnalyzer(scope)
    return analyzer.analyze_import_graph()
