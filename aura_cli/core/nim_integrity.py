"""Nim artifact integrity checker for Aura CLI startup.

Checks are deliberately non-blocking for the optional accelerator, but they
must not mistake a foreign native format, wrong architecture or missing
artifact for a healthy backend.  Runtime execution remains optional and is
never performed by import-time code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.nim_runtime import (
    is_compatible_native_binary,
    nim_executable_filename,
    nim_expected_artifacts,
    nim_library_filename,
    platform_bin_dirs,
)

logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).parent.parent.parent
_BIN_DIR: Optional[Path] = None


def _artifact_dir() -> Path:
    """Return the first existing platform directory containing artifacts."""
    if _BIN_DIR is not None:
        return _BIN_DIR
    directories = platform_bin_dirs()
    expected = nim_expected_artifacts()
    for path in directories:
        if path.is_dir() and any((path / name).exists() for name in expected):
            return path
    return directories[0]


# Startup is static-only.  Native smoke belongs to the release verifier/CI,
# never to import-time or application startup.  This also avoids the historical
# Sentinel ``--version`` side effect.
_BINARIES: Dict[str, Optional[List[str]]] = {
    "imagination": None,
    "nexus": None,
    "sentinel": None,
    "prism": None,
    "forge": None,
    "aura-monitor": None,
}

try:
    _LIBRARY = nim_library_filename()
except RuntimeError:
    _LIBRARY = "notebook.so"


@dataclass
class BinaryStatus:
    """Status of a single Nim binary."""

    name: str
    path: Path
    present: bool
    executable: bool
    smoke_ok: bool
    error: Optional[str] = None

    @property
    def ok(self) -> bool:
        """Return True if the binary is present and functional."""
        return self.present and self.executable and self.smoke_ok


@dataclass
class IntegrityReport:
    """Aggregated integrity report for all Nim binaries."""

    binaries: List[BinaryStatus] = field(default_factory=list)
    library_ok: bool = False
    library_path: Optional[Path] = None

    @property
    def all_ok(self) -> bool:
        """Return True if all binaries are healthy."""
        return all(b.ok for b in self.binaries) and self.library_ok

    @property
    def missing(self) -> List[str]:
        """Return list of missing binary names."""
        return [b.name for b in self.binaries if not b.present]

    @property
    def broken(self) -> List[str]:
        """Return list of broken binary names."""
        return [b.name for b in self.binaries if b.present and not b.ok]


def _check_binary(name: str, smoke_args: Optional[List[str]]) -> BinaryStatus:
    """Check a single binary for presence, native format and functionality."""
    path = _artifact_dir() / nim_executable_filename(name)
    present = path.is_file()
    executable = present and os.access(path, os.X_OK)
    smoke_ok = False
    error: Optional[str] = None

    if present and not executable:
        error = "executable bit missing"
    elif executable and not is_compatible_native_binary(path):
        executable = False
        error = "native format or architecture is incompatible with this host"
    elif executable:
        # Startup integrity is intentionally static-only; release smoke is opt-in.
        smoke_ok = True

    return BinaryStatus(
        name=name,
        path=path,
        present=present,
        executable=executable,
        smoke_ok=smoke_ok,
        error=error,
    )


def check_nim_integrity(verbose: bool = False) -> IntegrityReport:
    """Check all Nim binaries and the current-platform notebook library."""
    report = IntegrityReport()

    for name, smoke_args in _BINARIES.items():
        status = _check_binary(name, smoke_args)
        report.binaries.append(status)
        if verbose:
            icon = "OK" if status.ok else ("WARN" if status.present else "MISSING")
            logger.debug(
                "  %s %s: present=%s exec=%s smoke=%s",
                icon,
                name,
                status.present,
                status.executable,
                status.smoke_ok,
            )
            if status.error:
                logger.debug("     error: %s", status.error)

    lib_path = _artifact_dir() / _LIBRARY
    if not lib_path.is_file():
        packaged_path = Path(__file__).parent / "memory" / _LIBRARY
        if packaged_path.is_file():
            lib_path = packaged_path
    report.library_ok = lib_path.is_file() and is_compatible_native_binary(lib_path)
    report.library_path = lib_path if report.library_ok else None
    if verbose:
        icon = "OK" if report.library_ok else "MISSING"
        logger.debug("  %s %s: present=%s", icon, _LIBRARY, report.library_ok)

    return report


def log_integrity_summary(report: IntegrityReport) -> None:
    """Log a concise startup summary of Nim artifact status."""
    ok_count = sum(1 for b in report.binaries if b.ok)
    total = len(report.binaries)

    if report.all_ok:
        logger.info(
            "Nim F1 Engine: %s/%s binaries OK + notebook library OK", ok_count, total
        )
        return

    if report.missing:
        logger.warning(
            "Nim binaries missing (%s): %s. Python fallbacks active.",
            len(report.missing),
            ", ".join(report.missing),
        )
    if report.broken:
        logger.warning(
            "Nim binaries present but failing integrity/smoke: %s.",
            ", ".join(report.broken),
        )
    if not report.library_ok:
        logger.warning(
            "Nim notebook library (%s) not found or incompatible. Persistent memory uses Python fallback.",
            _LIBRARY,
        )
