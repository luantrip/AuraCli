"""Prism Bridge - interface for the Prism semantic chunker."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.nim_runtime import (
    resolve_nim_binary,
    resolve_nim_workspace_path,
    run_nim_process,
)

logger = get_logger(__name__)


@dataclass
class CodeChunk:
    """Represents a semantic chunk of code."""

    content: str
    start_line: int
    end_line: int
    kind: str
    name: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "content": self.content,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "kind": self.kind,
            "name": self.name,
        }


class PrismManager:
    """Manager for the Prism binary."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the manager."""
        self.project_root = (project_root or Path.cwd()).expanduser().resolve()
        self.executable_path = self._find_binary()
        self.last_error: Optional[str] = None

        if not self.executable_path:
            self.last_error = "Prism binary not found."
            logger.warning("Prism binary not found. Semantic chunking disabled.")

    def _find_binary(self) -> Optional[Path]:
        """Find the prism binary."""
        project_bin = Path(__file__).parent.parent.parent.parent / "bin" / "prism"
        return resolve_nim_binary("prism", extra_candidates=[project_bin])

    @property
    def available(self) -> bool:
        """Check if the Nim binary is available."""
        return self.executable_path is not None

    def chunk_file(self, file_path: str, max_chunk_size: int = 2000) -> List[CodeChunk]:
        """Chunk a code file semantically."""
        self.last_error = None
        if not self.available:
            self.last_error = "Prism binary is unavailable."
            return []
        if not 1 <= max_chunk_size <= 100_000:
            self.last_error = "Prism max_chunk_size must be between 1 and 100000."
            return []
        try:
            safe_file = resolve_nim_workspace_path(self.project_root, file_path)
        except ValueError as exc:
            self.last_error = str(exc)
            return []
        if not safe_file.is_file():
            self.last_error = f"Prism input file not found: {safe_file}"
            return []

        try:
            result = run_nim_process(
                [str(self.executable_path), str(safe_file), str(max_chunk_size)],
                cwd=self.project_root,
                timeout=30.0,
                max_output_bytes=4 * 1024 * 1024,
            )
            if result.timed_out:
                raise TimeoutError("Prism exceeded the 30-second timeout")
            if result.output_limited:
                raise ValueError("Prism exceeded the output size limit")
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    stderr[:500] or f"Prism exited with code {result.returncode}"
                )
            data = json.loads(result.stdout.decode("utf-8"))
            if not isinstance(data, list):
                raise ValueError("Prism output must be a JSON array")
            chunks: List[CodeChunk] = []
            for item in data:
                if not isinstance(item, dict) or not isinstance(
                    item.get("content"), str
                ):
                    raise ValueError("Prism chunk schema is invalid")
                start_line = item.get("start_line", 0)
                end_line = item.get("end_line", 0)
                if not isinstance(start_line, int) or not isinstance(end_line, int):
                    raise ValueError("Prism chunk line numbers are invalid")
                chunks.append(
                    CodeChunk(
                        content=item["content"],
                        start_line=start_line,
                        end_line=end_line,
                        kind=str(item.get("kind", "unknown")),
                        name=str(item.get("name", "")),
                    )
                )
            return chunks
        except json.JSONDecodeError as exc:
            self.last_error = f"Prism returned invalid JSON for {safe_file}: {exc}"
            logger.error(self.last_error)
            return []
        except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
            self.last_error = f"Error running Prism: {exc}"
            logger.error(self.last_error)
            return []
