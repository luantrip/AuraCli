"""Monitor Manager - bridge for the Nim headless browser."""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse

from aura_cli.core.logger import get_logger
from aura_cli.core.nim_runtime import (
    resolve_nim_binary,
    resolve_nim_workspace_path,
    run_nim_process,
)

logger = get_logger(__name__)


class MonitorManager:
    """Manager for the aura-monitor binary."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the manager."""
        self.project_root = (project_root or Path.cwd()).expanduser().resolve()
        self.executable_path = self._find_binary()
        self.last_error: Optional[str] = None

        if not self.executable_path:
            self.last_error = "Monitor binary not found."
            logger.warning(
                "Monitor binary not found. Navegação web/conteúdo desabilitada."
            )

    def _find_binary(self) -> Optional[Path]:
        """Locate the Nim binary in the filesystem."""
        project_bin = (
            Path(__file__).parent.parent.parent.parent / "bin" / "aura-monitor"
        )
        return resolve_nim_binary("aura-monitor", extra_candidates=[project_bin])

    @property
    def available(self) -> bool:
        """Check if the Nim binary is available."""
        return self.executable_path is not None

    def _validate_source(self, source: str) -> str:
        """Return a safe URL or a contained local file path."""
        if not isinstance(source, str) or not source.strip():
            raise ValueError("Monitor source cannot be empty")
        if "\x00" in source:
            raise ValueError("Monitor source contains null bytes")
        parsed = urlparse(source)
        if parsed.scheme:
            if parsed.scheme not in {"http", "https"}:
                raise ValueError("Monitor only allows http and https URLs")
            if parsed.username or parsed.password or not parsed.hostname:
                raise ValueError(
                    "Monitor URL must not contain credentials and needs a host"
                )
            hostname = parsed.hostname.lower().rstrip(".")
            if hostname in {"localhost", "localhost.localdomain"}:
                raise ValueError("Monitor refuses localhost URLs")
            try:
                address = ipaddress.ip_address(hostname)
            except ValueError:
                address = None
            if address is not None and (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_reserved
                or address.is_multicast
            ):
                raise ValueError("Monitor refuses private or local IP URLs")
            return source
        return str(resolve_nim_workspace_path(self.project_root, source))

    def browse(
        self, source: str, render_mode: str = "text"
    ) -> Optional[Dict[str, Any]]:
        """Browse an allowed URL/path and return rendered content."""
        self.last_error = None
        if not self.available:
            self.last_error = "Monitor binary is unavailable."
            return None
        if render_mode not in {"text", "json"}:
            self.last_error = "Monitor render_mode must be 'text' or 'json'."
            return None

        try:
            validated_source = self._validate_source(source)
            cmd = [str(self.executable_path), "--dump", validated_source]
            if render_mode == "json":
                cmd.append("--json")
            else:
                cmd.extend(["--width", "100"])

            result = run_nim_process(
                cmd,
                cwd=self.project_root,
                timeout=30.0,
                max_output_bytes=4 * 1024 * 1024,
            )
            if result.timed_out:
                raise TimeoutError("Monitor excedeu o timeout de 30 segundos")
            if result.output_limited:
                raise ValueError("Monitor excedeu o limite de saída")
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    stderr[:500] or f"Monitor exited with code {result.returncode}"
                )

            output = result.stdout.decode("utf-8")
            if render_mode == "json":
                parsed_output = json.loads(output)
                payload: Dict[str, Any] = {
                    "source": source,
                    "render_mode": "json",
                    "backend": "nim",
                }
                if isinstance(parsed_output, dict):
                    payload.update(parsed_output)
                else:
                    payload["content"] = parsed_output
                return payload

            return {
                "source": source,
                "render_mode": "text",
                "backend": "nim",
                "content": output,
            }
        except json.JSONDecodeError as exc:
            self.last_error = f"Monitor returned invalid JSON: {exc}"
            logger.error(self.last_error)
            return None
        except (OSError, ValueError, RuntimeError, TimeoutError) as exc:
            self.last_error = f"Error running Monitor: {exc}"
            logger.error(self.last_error)
            return None
