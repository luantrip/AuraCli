"""Sentinel Manager - interface for the Sentinel Nim change detector."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.nim_runtime import resolve_nim_binary, run_nim_process

logger = get_logger(__name__)


@dataclass
class FileDiff:
    """Represents changes in the file system."""

    added: List[str]
    modified: List[str]
    deleted: List[str]
    stats: Dict[str, int]

    @property
    def has_changes(self) -> bool:
        """Return True if file changes were detected."""
        return bool(self.added or self.modified or self.deleted)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "added": self.added,
            "modified": self.modified,
            "deleted": self.deleted,
            "stats": self.stats,
        }


class SentinelManager:
    """Manager for the Sentinel binary."""

    def __init__(self, project_root: Path):
        """Initialize the manager."""
        self.project_root = project_root.expanduser().resolve()
        self.executable_path = self._find_binary()
        self.last_error: Optional[str] = None
        from aura_cli.core.paths import ArtifactLayout

        self.state_file = (
            ArtifactLayout(self.project_root)
            .project("sentinel_state.json")
            .expanduser()
            .resolve()
        )
        try:
            self.state_file.relative_to(self.project_root)
        except ValueError:
            self.executable_path = None
            self.last_error = "Sentinel state path escapes the project workspace."

        if not self.executable_path:
            self.last_error = self.last_error or "Sentinel binary not found."
            logger.warning(
                "Sentinel binary not found or unsafe state. Detection disabled."
            )

    def _find_binary(self) -> Optional[Path]:
        """Find the sentinel binary."""
        project_bin = Path(__file__).parent.parent.parent.parent / "bin" / "sentinel"
        return resolve_nim_binary("sentinel", extra_candidates=[project_bin])

    @property
    def available(self) -> bool:
        """Check if the Nim binary is available."""
        return self.executable_path is not None

    def scan_changes(self) -> Optional[FileDiff]:
        """Scan for changes since last run using Sentinel."""
        self.last_error = None
        if not self.available:
            self.last_error = "Sentinel binary is unavailable."
            return None

        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = run_nim_process(
                [
                    str(self.executable_path),
                    str(self.project_root),
                    str(self.state_file),
                ],
                cwd=self.project_root,
                timeout=30.0,
                max_output_bytes=2 * 1024 * 1024,
            )
            if result.timed_out:
                raise TimeoutError("Sentinel excedeu o timeout de 30 segundos")
            if result.output_limited:
                raise ValueError("Sentinel excedeu o limite de saída")
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    stderr[:500] or f"Sentinel exited with code {result.returncode}"
                )
            data = json.loads(result.stdout.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Sentinel output must be a JSON object")
            added = data.get("added", [])
            modified = data.get("modified", [])
            deleted = data.get("deleted", [])
            stats = data.get("stats", {})
            if not all(isinstance(value, list) for value in (added, modified, deleted)):
                raise ValueError("Sentinel diff lists are invalid")
            if not isinstance(stats, dict):
                raise ValueError("Sentinel stats are invalid")
            return FileDiff(
                added=[str(value) for value in added],
                modified=[str(value) for value in modified],
                deleted=[str(value) for value in deleted],
                stats={
                    str(key): int(value)
                    for key, value in stats.items()
                    if isinstance(value, int)
                },
            )
        except (
            OSError,
            ValueError,
            RuntimeError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            self.last_error = f"Sentinel failed: {exc}"
            logger.error(self.last_error)
            return None

    def reset_state(self) -> bool:
        """Reset the stored state (forcing a full re-scan next time)."""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
            self.last_error = None
            return True
        except OSError as exc:
            self.last_error = f"Failed to reset sentinel state: {exc}"
            logger.error(self.last_error)
            return False
