"""Graph Service - interface for the Nexus dependency graph."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Dict, List, Optional, Set

from aura_cli.core.logger import get_logger
from aura_cli.core.nim_runtime import (
    resolve_nim_binary,
    run_nim_process,
)

logger = get_logger(__name__)


@dataclass
class DependencyGraph:
    """Represents the project dependency graph."""

    nodes: Set[str]
    dependencies: Dict[str, List[str]]
    dependents: Dict[str, List[str]]

    def get_dependencies(self, file_path: str) -> List[str]:
        """Get list of files imported by file_path."""
        return self.dependencies.get(file_path, [])

    def get_dependents(self, file_path: str) -> List[str]:
        """Get list of files that import file_path."""
        return self.dependents.get(file_path, [])


class GraphService:
    """Manager for the Nexus binary with a Python fallback."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the instance."""
        self.project_root = (project_root or Path.cwd()).expanduser().resolve()
        self.executable_path = self._find_binary()
        self.last_error: Optional[str] = None
        self.backend = "nim" if self.executable_path else "python"

        if not self.executable_path:
            self.last_error = "Nexus binary not found."
            logger.warning(
                "Nexus binary not found. Análise Python de dependências será usada."
            )

    def _find_binary(self) -> Optional[Path]:
        """Find the nexus binary."""
        project_bin = Path(__file__).parent.parent.parent.parent / "bin" / "nexus"
        return resolve_nim_binary("nexus", extra_candidates=[project_bin])

    @property
    def available(self) -> bool:
        """Check if the graph service native backend is available."""
        return self.executable_path is not None

    def _python_fallback(self) -> DependencyGraph:
        """Build the same graph contract using the local AST analyzer."""
        from aura_cli.core.dependency_analysis import DependencyAnalyzer

        analyzer = DependencyAnalyzer(str(self.project_root)).analyze()
        self.backend = "python"
        dependencies = {
            path: sorted(values) for path, values in analyzer.file_dependencies.items()
        }
        dependents = {
            path: sorted(values) for path, values in analyzer.file_dependents.items()
        }
        nodes = set(analyzer._python_files) | set(dependencies) | set(dependents)
        return DependencyGraph(
            nodes=nodes, dependencies=dependencies, dependents=dependents
        )

    def build_graph(self) -> Optional[DependencyGraph]:
        """Build dependency graph using Nexus or the safe Python fallback."""
        self.last_error = None
        if not self.available:
            try:
                return self._python_fallback()
            except Exception as exc:
                self.last_error = f"Nexus/Python fallback failed: {exc}"
                logger.error(self.last_error)
                return None

        try:
            result = run_nim_process(
                [str(self.executable_path), str(self.project_root)],
                cwd=self.project_root,
                timeout=30.0,
                max_output_bytes=4 * 1024 * 1024,
            )
            if result.timed_out:
                raise TimeoutError("Nexus excedeu o timeout de 30 segundos")
            if result.output_limited:
                raise ValueError("Nexus excedeu o limite de saída")
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    stderr[:500] or f"Nexus exited with code {result.returncode}"
                )
            data = json.loads(result.stdout.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Nexus output must be a JSON object")
            dependencies = data.get("dependencies", {})
            dependents = data.get("dependents", {})
            nodes = data.get("nodes", [])
            if (
                not isinstance(dependencies, dict)
                or not isinstance(dependents, dict)
                or not isinstance(nodes, list)
            ):
                raise ValueError("Nexus output schema is invalid")
            self.backend = "nim"
            return DependencyGraph(
                nodes={str(node) for node in nodes},
                dependencies={
                    str(key): [str(item) for item in value]
                    for key, value in dependencies.items()
                    if isinstance(value, list)
                },
                dependents={
                    str(key): [str(item) for item in value]
                    for key, value in dependents.items()
                    if isinstance(value, list)
                },
            )
        except (
            OSError,
            ValueError,
            RuntimeError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            self.last_error = f"Nexus failed: {exc}"
            logger.warning("%s; usando fallback Python", self.last_error)
            try:
                return self._python_fallback()
            except Exception as fallback_exc:
                self.last_error = f"{self.last_error}; fallback failed: {fallback_exc}"
                logger.error(self.last_error)
                return None
