"""Imagination Manager - bridge for the Nim filesystem scanner."""

from __future__ import annotations

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


class ImaginationManager:
    """Manager for the Imagination binary."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the scanner manager."""
        self.project_root = (project_root or Path.cwd()).expanduser().resolve()
        self.executable_path = self._find_binary()
        self.last_error: Optional[str] = None

        if not self.executable_path:
            self.last_error = "Imagination binary not found."
            logger.warning(
                "Imagination binary not found. Aceleração de varredura do projeto desabilitada."
            )

    def _find_binary(self) -> Optional[Path]:
        """Locate the Nim binary in the filesystem."""
        project_bin = Path(__file__).parent.parent.parent.parent / "bin" / "imagination"
        return resolve_nim_binary("imagination", extra_candidates=[project_bin])

    @property
    def available(self) -> bool:
        """Check if the Nim binary is available."""
        return self.executable_path is not None

    def scan_project(
        self,
        path: str = ".",
        context: Optional[str] = None,
        limit: int = 10,
        no_preview: bool = False,
    ) -> Optional[Dict[str, Any]]:
        """Scan a directory using the Nim Imagination engine."""
        self.last_error = None
        if not self.available:
            self.last_error = "Imagination binary is unavailable."
            return None
        if not 1 <= limit <= 1000:
            self.last_error = "Imagination limit must be between 1 and 1000."
            return None
        if context is not None and len(context) > 4096:
            self.last_error = "Imagination context exceeds 4096 characters."
            return None

        try:
            target = resolve_nim_workspace_path(self.project_root, path)
        except ValueError as exc:
            self.last_error = str(exc)
            return None

        cmd = [str(self.executable_path), str(target), "--json"]
        if context:
            cmd.extend(["--context", context, "--limit", str(limit)])
        if no_preview:
            cmd.append("--no-preview")

        try:
            result = run_nim_process(
                cmd,
                cwd=self.project_root,
                timeout=60.0,
                max_output_bytes=4 * 1024 * 1024,
            )
            if result.timed_out:
                self.last_error = "Imagination excedeu o timeout de 60 segundos."
                return None
            if result.output_limited:
                self.last_error = "Imagination excedeu o limite de saída."
                return None
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                self.last_error = (
                    stderr[:500] or f"Imagination exited with code {result.returncode}"
                )
                logger.error("Imagination failed: %s", self.last_error)
                return None
            payload = json.loads(result.stdout.decode("utf-8"))
            if not isinstance(payload, dict):
                raise ValueError("Imagination output must be a JSON object")
            return payload
        except json.JSONDecodeError as exc:
            self.last_error = f"Imagination returned invalid JSON: {exc}"
            logger.error("Imagination returned invalid JSON: %s", exc)
            return None
        except (OSError, ValueError) as exc:
            self.last_error = f"Error running Imagination: {exc}"
            logger.error("Error running Imagination: %s", exc)
            return None

    def scan(
        self,
        target_path: str,
        no_preview: bool = True,
        context_keywords: Optional[List[str]] = None,
        limit: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """Backwards-compatible API used by legacy callers."""
        context = " ".join(context_keywords) if context_keywords else None
        return self.scan_project(
            path=target_path,
            context=context,
            limit=limit,
            no_preview=no_preview,
        )
