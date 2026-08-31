"""Specialised integration with the Aura Forge binary."""

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.nim_runtime import resolve_nim_binary, run_nim_process

logger = get_logger(__name__)


@dataclass
class ForgeResult:
    """Result of code forging."""

    success: bool
    code: str
    errors: List[str]
    logs: List[str]
    status: str = "ok"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "code": self.code,
            "errors": self.errors,
            "logs": self.logs,
            "status": self.status,
        }


class ForgeManager:
    """Specialised wrapper for the Forge binary."""

    def __init__(self):
        """Initialize the manager."""
        self.executable_path = self._find_binary()
        self.last_error: Optional[str] = None

        if not self.executable_path:
            self.last_error = "Forge binary not found."
            logger.warning(
                "Forge binary not found. Sandbox de código desabilitado."
            )

    def _find_binary(self) -> Optional[Path]:
        """Find the forge binary."""
        project_bin = Path(__file__).parent.parent.parent.parent / "bin" / "forge"
        return resolve_nim_binary("forge", extra_candidates=[project_bin])

    @property
    def available(self) -> bool:
        """Check if the Nim binary is available."""
        return self.executable_path is not None

    def validate_and_fix(
        self, code: str, language: str = "python", fix: bool = True
    ) -> ForgeResult:
        """Run code through Forge with an explicit bounded contract."""
        self.last_error = None
        if not self.available:
            self.last_error = "Forge binary is unavailable."
            return ForgeResult(
                success=False,
                code=code,
                errors=[self.last_error],
                logs=[],
                status="unavailable",
            )
        if len(code.encode("utf-8")) > 10 * 1024 * 1024:
            self.last_error = "Forge input exceeds 10 MiB."
            return ForgeResult(False, code, [self.last_error], [], "rejected")
        if not language or len(language) > 32:
            self.last_error = "Forge language is invalid."
            return ForgeResult(False, code, [self.last_error], [], "rejected")

        try:
            input_json = json.dumps(
                {"code": code, "language": language, "fix": bool(fix)},
                ensure_ascii=False,
            )
            result = run_nim_process(
                [str(self.executable_path)],
                cwd=Path.cwd(),
                timeout=30.0,
                max_output_bytes=4 * 1024 * 1024,
                input_text=input_json,
            )
            if result.timed_out:
                raise TimeoutError("Forge excedeu o timeout de 30 segundos")
            if result.output_limited:
                raise ValueError("Forge excedeu o limite de saída")
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace").strip()
                raise RuntimeError(
                    stderr[:500] or f"Forge exited with code {result.returncode}"
                )
            data = json.loads(result.stdout.decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError("Forge output must be a JSON object")
            result_code = data.get("code", code)
            errors = data.get("errors", [])
            logs = data.get("logs", [])
            if (
                not isinstance(result_code, str)
                or not isinstance(errors, list)
                or not isinstance(logs, list)
            ):
                raise ValueError("Forge output schema is invalid")
            return ForgeResult(
                success=bool(data.get("success", False)),
                code=result_code,
                errors=[str(item) for item in errors],
                logs=[str(item) for item in logs],
                status="ok" if bool(data.get("success", False)) else "failed",
            )
        except (
            OSError,
            ValueError,
            RuntimeError,
            TimeoutError,
            json.JSONDecodeError,
        ) as exc:
            self.last_error = f"Forge failed: {exc}"
            logger.error(self.last_error)
            return ForgeResult(
                success=False,
                code=code,
                errors=[self.last_error],
                logs=[],
                status="error",
            )

    def analyze(
        self,
        files: List[Dict[str, str]],
        checks: Optional[List[str]] = None,
        thresholds: Optional[Dict[str, int]] = None,
    ) -> Dict[str, Any]:
        """Run native analysis via Forge, falling back explicitly to Python."""
        default = ["complexity", "deadcode", "style", "duplicates", "security"]
        all_checks = checks or default
        config = {"checks": all_checks, "thresholds": thresholds or {}}

        if self.available:
            try:
                payload = {"mode": "analyze", "files": files, "config": config}
                result = run_nim_process(
                    [str(self.executable_path)],
                    cwd=Path.cwd(),
                    timeout=30.0,
                    max_output_bytes=8 * 1024 * 1024,
                    input_text=json.dumps(payload, ensure_ascii=False),
                )
                if result.timed_out:
                    raise TimeoutError("Forge analyze excedeu o timeout de 30 segundos")
                if result.output_limited:
                    raise ValueError("Forge analyze excedeu o limite de saída")
                if result.returncode != 0:
                    stderr = result.stderr.decode("utf-8", errors="replace").strip()
                    raise RuntimeError(
                        stderr[:500] or f"Forge exited with code {result.returncode}"
                    )
                output = json.loads(result.stdout.decode("utf-8"))
                if isinstance(output, dict) and output.get("success") is True:
                    output.setdefault("backend", "nim")
                    return output
                raise ValueError("Forge analyze returned an unsuccessful result")
            except (
                OSError,
                ValueError,
                RuntimeError,
                TimeoutError,
                json.JSONDecodeError,
            ) as exc:
                logger.warning("Forge analyze failed, using Python fallback: %s", exc)

        fallback = self._python_fallback(files, all_checks)
        fallback["backend"] = "python"
        fallback["status"] = "fallback"
        return fallback

    def _python_fallback(
        self, files: List[Dict[str, str]], checks: List[str]
    ) -> Dict[str, Any]:
        """Run analysis using Python modules."""
        import time

        from aura_cli.core.quality import (
            analyze_complexity,
            check_style,
            detect_dead_code,
            detect_duplicates,
            scan_security,
        )

        start = time.time()
        findings: List[Dict[str, Any]] = []
        for f in files:
            src, path = f["content"], f["path"]
            if "complexity" in checks:
                findings.extend(analyze_complexity(src, path))
            if "deadcode" in checks:
                findings.extend(detect_dead_code(src, path))
            if "style" in checks:
                findings.extend(check_style(src, path))
            if "duplicates" in checks:
                findings.extend(detect_duplicates(src, path))
            if "security" in checks:
                findings.extend(scan_security(src, path))
        duration = int((time.time() - start) * 1000)
        return {
            "success": True,
            "findings": findings,
            "stats": {
                "files_analyzed": len(files),
                "total_findings": len(findings),
                "duration_ms": duration,
                "engine": "python",
            },
        }


_forge_manager: Optional["ForgeManager"] = None


def get_forge_manager() -> "ForgeManager":
    """Get singleton ForgeManager."""
    global _forge_manager
    if _forge_manager is None:
        _forge_manager = ForgeManager()
    return _forge_manager
