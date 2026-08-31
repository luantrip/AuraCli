"""CodebaseContextManager — manages codebase analysis context."""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class CodebaseContextManager:
    """Manages codebase analysis context (traversal, AST, symbols, dependencies)."""

    def __init__(self, root_path: str):
        """Initialise the context manager."""
        self.root_path = Path(root_path).resolve()
        self.files_analyzed: List[Dict[str, Any]] = []
        self.symbols_index: Dict[str, List[Dict[str, Any]]] = {
            "classes": [],
            "functions": [],
            "variables": [],
            "imports": [],
        }
        self.dependency_graph: Optional[Any] = None
        self.metadata: Dict[str, Any] = {
            "analysis_start": None,
            "analysis_end": None,
            "total_files": 0,
            "total_lines": 0,
            "languages": {},
        }

        logger.info(f"CodebaseContextManager initialized for: {self.root_path}")

    def start_analysis(self):
        """Mark the start of the analysis."""
        self.metadata["analysis_start"] = datetime.now()
        logger.debug("Análise iniciada")

    def end_analysis(self):
        """Mark the end of the analysis."""
        self.metadata["analysis_end"] = datetime.now()
        duration = (
            self.metadata["analysis_end"] - self.metadata["analysis_start"]
        ).total_seconds()
        self.metadata["duration"] = duration
        logger.info(f"Análise concluída em {duration:.2f}s")

    def store_file_analysis(self, file_path: str, ast_data: Dict[str, Any]):
        """Store analysis results for a file."""
        file_info = {
            "path": file_path,
            "ast_data": ast_data,
            "analyzed_at": datetime.now().isoformat(),
        }

        self.files_analyzed.append(file_info)
        self.metadata["total_files"] += 1

        if "classes" in ast_data:
            for class_name in ast_data["classes"]:
                self.symbols_index["classes"].append(
                    {
                        "name": class_name,
                        "file": file_path,
                        "type": "class",
                    }
                )

        if "functions" in ast_data:
            for func_name in ast_data["functions"]:
                self.symbols_index["functions"].append(
                    {
                        "name": func_name,
                        "file": file_path,
                        "type": "function",
                    }
                )

        if "variables" in ast_data:
            for var_name in ast_data["variables"]:
                self.symbols_index["variables"].append(
                    {
                        "name": var_name,
                        "file": file_path,
                        "type": "variable",
                    }
                )

        if "imports" in ast_data:
            for import_name in ast_data["imports"]:
                self.symbols_index["imports"].append(
                    {
                        "name": import_name,
                        "file": file_path,
                        "type": "import",
                    }
                )

        file_ext = Path(file_path).suffix
        if file_ext:
            self.metadata["languages"][file_ext] = (
                self.metadata["languages"].get(file_ext, 0) + 1
            )

        logger.debug(f"File analyzed and stored: {file_path}")

    def get_symbols_by_type(self, symbol_type: str) -> List[Dict[str, Any]]:
        """Return symbols filtered by type."""
        return self.symbols_index.get(symbol_type, [])

    def search_symbol(self, symbol_name: str) -> List[Dict[str, Any]]:
        """Search for a symbol by name."""
        results = []

        for symbols in self.symbols_index.values():
            for symbol in symbols:
                if symbol["name"] == symbol_name:
                    results.append(symbol)

        return results

    def get_files_by_extension(self, extension: str) -> List[str]:
        """Return files filtered by extension."""
        return [
            file_info["path"]
            for file_info in self.files_analyzed
            if Path(file_info["path"]).suffix == extension
        ]

    def get_summary(self) -> Dict[str, Any]:
        """Return a summary of the codebase context."""
        return {
            "root_path": str(self.root_path),
            "files_analyzed": self.metadata["total_files"],
            "total_lines": self.metadata["total_lines"],
            "languages": self.metadata["languages"],
            "symbols": {
                "classes": len(self.symbols_index["classes"]),
                "functions": len(self.symbols_index["functions"]),
                "variables": len(self.symbols_index["variables"]),
                "imports": len(self.symbols_index["imports"]),
            },
            "duration": self.metadata.get("duration", 0),
            "analysis_start": self.metadata.get("analysis_start"),
            "analysis_end": self.metadata.get("analysis_end"),
        }

    def clear(self):
        """Limpa todos os dados armazenados."""
        self.files_analyzed.clear()
        for symbol_type in self.symbols_index:
            self.symbols_index[symbol_type].clear()
        self.dependency_graph = None
        self.metadata = {
            "analysis_start": None,
            "analysis_end": None,
            "total_files": 0,
            "total_lines": 0,
            "languages": {},
        }
        logger.debug("Contexto limpo")
