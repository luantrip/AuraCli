"""Runtime helpers for resolving and validating Aura's Nim artifacts.

The optional ``aura-cli-nim`` distribution and the repository staging tree use
this module's canonical platform/tag and filename rules.  Resolution remains
side-effect free: it only inspects paths and bytes; loading a shared library or
starting an executable is handled by the caller.
"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import platform
import shutil
import struct
import subprocess
import sys
import threading
from typing import Any, Dict, Iterable, List, Optional

from aura_cli.core.config import get_config_manager
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_NIM_EXECUTABLES = (
    "imagination",
    "nexus",
    "sentinel",
    "prism",
    "forge",
    "aura-monitor",
)
_PLATFORM_NAMES = {"linux", "macos", "windows"}
_ARCH_ALIASES = {
    "amd64": "x86_64",
    "x64": "x86_64",
    "x86_64": "x86_64",
    "arm64": "aarch64",
    "aarch64": "aarch64",
}
_ELF_MACHINES = {"x86_64": 0x3E, "aarch64": 0xB7}
_MACHO_CPUS = {"x86_64": 0x01000007, "aarch64": 0x0100000C}
_PE_MACHINES = {"x86_64": 0x8664, "aarch64": 0xAA64}


@dataclass(frozen=True)
class NimProcessResult:
    """Bounded result from a Nim subprocess."""

    returncode: int
    stdout: bytes
    stderr: bytes
    timed_out: bool = False
    output_limited: bool = False


@dataclass(frozen=True)
class NimTarget:
    """Canonical platform target used by all native artifact paths."""

    platform: str
    architecture: str

    @property
    def tag(self) -> str:
        """Return the canonical ``platform-architecture`` tag."""
        return f"{self.platform}-{self.architecture}"

    @property
    def library_extension(self) -> str:
        """Return the platform shared-library extension without a dot."""
        return {"linux": "so", "macos": "dylib", "windows": "dll"}[self.platform]


def canonical_architecture(machine: str) -> str:
    """Normalize common ``platform.machine()`` values."""
    normalized = machine.strip().lower()
    return _ARCH_ALIASES.get(normalized, normalized)


def canonical_platform(system: str) -> str:
    """Normalize a Python platform identifier to Aura's platform name."""
    normalized = system.strip().lower()
    return {
        "darwin": "macos",
        "mac": "macos",
        "win32": "windows",
        "windows": "windows",
        "linux": "linux",
    }.get(normalized, normalized)


def nim_target_for_current_platform() -> NimTarget:
    """Return the canonical target for the current interpreter host."""
    target = NimTarget(
        canonical_platform(sys.platform),
        canonical_architecture(platform.machine()),
    )
    if target.platform not in _PLATFORM_NAMES:
        raise RuntimeError(
            f"Unsupported host platform for Nim artifacts: {target.platform}"
        )
    return target


def parse_nim_target(tag: str) -> NimTarget:
    """Parse and validate a canonical Nim target tag."""
    try:
        system, architecture = tag.strip().lower().split("-", 1)
    except ValueError as exc:
        raise ValueError(f"Invalid Nim target tag: {tag!r}") from exc
    system = canonical_platform(system)
    architecture = canonical_architecture(architecture)
    if system not in _PLATFORM_NAMES:
        raise ValueError(f"Unsupported Nim platform: {system}")
    if (
        not architecture
        or architecture != architecture.strip()
        or architecture not in _ARCH_ALIASES.values()
    ):
        raise ValueError(f"Invalid Nim architecture: {architecture!r}")
    return NimTarget(system, architecture)


def nim_platform_tag() -> str:
    """Return the canonical directory tag used by Aura native artifacts."""
    return nim_target_for_current_platform().tag


def nim_library_extension() -> str:
    """Return the current platform library extension, including the dot."""
    return f".{nim_target_for_current_platform().library_extension}"


def nim_executable_filename(name: str, *, target: Optional[NimTarget] = None) -> str:
    """Return the canonical filename for an executable component."""
    target = target or nim_target_for_current_platform()
    if name.endswith(".exe"):
        return name
    return f"{name}.exe" if target.platform == "windows" else name


def nim_library_filename(
    name: str = "notebook", *, target: Optional[NimTarget] = None
) -> str:
    """Return the canonical filename for a shared library component."""
    target = target or nim_target_for_current_platform()
    bare_name = name
    for extension in (".so", ".dylib", ".dll"):
        if bare_name.endswith(extension):
            bare_name = bare_name[: -len(extension)]
            break
    return f"{bare_name}.{target.library_extension}"


def nim_expected_artifacts(tag: Optional[str] = None) -> tuple[str, ...]:
    """Return the complete ordered artifact set for a target."""
    target = (
        parse_nim_target(tag) if tag is not None else nim_target_for_current_platform()
    )
    return tuple(
        [nim_executable_filename(name, target=target) for name in _NIM_EXECUTABLES]
        + [nim_library_filename("notebook", target=target)]
    )


def platform_bin_dirs() -> List[Path]:
    """Return native artifact directories in secure precedence order.

    The optional ``aura-cli-nim`` package owns released artifacts.  The
    repository ``bin/`` directory is a local build/staging fallback.
    """
    tag = nim_platform_tag()
    directories: List[Path] = []
    try:
        from aura_cli_nim import get_platform_bin_dir

        directories.append(Path(get_platform_bin_dir()))
    except (ImportError, AttributeError, OSError, RuntimeError):
        pass
    directories.append(_PROJECT_ROOT / "bin" / tag)
    return _dedupe_paths(directories)


def _read_prefix(path: Path, size: int = 4096) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(size)
    except (OSError, ValueError):
        return b""


def _elf_matches_architecture(data: bytes, architecture: str) -> bool:
    if len(data) < 20 or data[:4] != b"\x7fELF":
        return False
    elf_class = data[4]
    if architecture == "x86_64" and elf_class != 2:
        return False
    if architecture == "aarch64" and elf_class != 2:
        return False
    endian = "<" if data[5] == 1 else ">" if data[5] == 2 else ""
    if not endian:
        return False
    machine = struct.unpack_from(f"{endian}H", data, 18)[0]
    return machine == _ELF_MACHINES.get(architecture)


def _macho_matches_architecture(data: bytes, architecture: str) -> bool:
    if len(data) < 8:
        return False
    expected = _MACHO_CPUS.get(architecture)
    if expected is None:
        return False
    magic = data[:4]
    if magic in {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"}:
        endian = "<" if magic == b"\xcf\xfa\xed\xfe" else ">"
        return struct.unpack_from(f"{endian}I", data, 4)[0] == expected
    if magic == b"\xca\xfe\xba\xbe":
        endian = ">"
    elif magic == b"\xbe\xba\xfe\xca":
        endian = "<"
    else:
        return False
    if len(data) < 8:
        return False
    count = struct.unpack_from(f"{endian}I", data, 4)[0]
    offset = 8
    for _ in range(min(count, 64)):
        if offset + 20 > len(data):
            break
        cputype = struct.unpack_from(f"{endian}I", data, offset)[0]
        if cputype == expected:
            return True
        offset += 20
    return False


def _pe_matches_architecture(data: bytes, architecture: str) -> bool:
    if len(data) < 64 or data[:2] != b"MZ":
        return False
    pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
    if pe_offset < 0 or pe_offset + 6 > len(data):
        return False
    if data[pe_offset : pe_offset + 4] != b"PE\0\0":
        return False
    machine = struct.unpack_from("<H", data, pe_offset + 4)[0]
    return machine == _PE_MACHINES.get(architecture)


def is_compatible_native_binary(path: Path) -> bool:
    """Return whether a native artifact matches the current OS and CPU.

    Scripts are deliberately rejected.  Native overrides must be actual
    binaries so that a PATH/configuration mistake cannot silently execute an
    arbitrary shebang file under a native component name.
    """
    data = _read_prefix(Path(path))
    if not data:
        return False
    try:
        target = nim_target_for_current_platform()
    except RuntimeError:
        return False
    if target.platform == "linux":
        return _elf_matches_architecture(data, target.architecture)
    if target.platform == "macos":
        return _macho_matches_architecture(data, target.architecture)
    if target.platform == "windows":
        return _pe_matches_architecture(data, target.architecture)
    return False


def _dedupe_paths(paths: Iterable[Path]) -> List[Path]:
    """Return unique paths preserving insertion order."""
    seen = set()
    unique: List[Path] = []
    for path in paths:
        normalized = os.path.normcase(str(Path(path).expanduser()))
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(Path(path).expanduser())
    return unique


def _artifact_filename(target_name: str, kind: str) -> str:
    target = nim_target_for_current_platform()
    if kind == "binary":
        return nim_executable_filename(target_name, target=target)
    if kind == "library":
        return nim_library_filename(target_name, target=target)
    raise ValueError(f"Unknown Nim artifact kind: {kind}")


def configured_nim_candidates(target_name: str, *, kind: str = "binary") -> List[Path]:
    """Build candidates from ``nim_binary_path`` configuration.

    A configured directory is expanded with the canonical target filename.  A
    configured file is accepted only when its basename is the requested
    canonical filename; this prevents one component from silently receiving a
    different component's artifact.
    """
    candidates: List[Path] = []
    try:
        configured = get_config_manager().get("nim_binary_path")
        if not configured:
            return candidates
        base = Path(str(configured)).expanduser()
        filename = _artifact_filename(target_name, kind)
        if base.is_file():
            if base.name == filename:
                candidates.append(base)
        elif base.is_dir():
            candidates.append(base / filename)
    except (OSError, ValueError, TypeError) as exc:
        logger.debug("Failed to read nim_binary_path for %s: %s", target_name, exc)
    except Exception as exc:
        logger.debug("Failed to read nim_binary_path for %s: %s", target_name, exc)
    return _dedupe_paths(candidates)


def build_nim_candidates(
    target_name: str,
    extra_candidates: Optional[Iterable[Path]] = None,
    *,
    kind: str = "binary",
) -> List[Path]:
    """Build candidates for a canonical Nim artifact."""
    filename = _artifact_filename(target_name, kind)
    candidates = configured_nim_candidates(target_name, kind=kind)
    candidates.extend(directory / filename for directory in platform_bin_dirs())
    if extra_candidates:
        for candidate in extra_candidates:
            candidate_path = Path(candidate).expanduser()
            if candidate_path.name in {target_name, filename}:
                candidates.append(candidate_path)
            elif candidate_path.is_dir():
                candidates.append(candidate_path / filename)
    return _dedupe_paths(candidates)


def resolve_nim_binary(
    binary_name: str, extra_candidates: Optional[Iterable[Path]] = None
) -> Optional[Path]:
    """Resolve an executable Nim binary path without executing it."""
    for candidate in build_nim_candidates(binary_name, extra_candidates, kind="binary"):
        if (
            candidate.is_file()
            and os.access(candidate, os.X_OK)
            and is_compatible_native_binary(candidate)
        ):
            return candidate

    try:
        lookup_name = nim_executable_filename(binary_name)
    except RuntimeError:
        lookup_name = binary_name
    system_path = shutil.which(lookup_name)
    if system_path:
        path = Path(system_path)
        if (
            path.is_file()
            and os.access(path, os.X_OK)
            and is_compatible_native_binary(path)
        ):
            return path
    return None


def resolve_nim_library(
    library_name: str, extra_candidates: Optional[Iterable[Path]] = None
) -> Optional[Path]:
    """Resolve a readable, current-platform shared library path."""
    for candidate in build_nim_candidates(
        library_name, extra_candidates, kind="library"
    ):
        if (
            candidate.is_file()
            and os.access(candidate, os.R_OK)
            and is_compatible_native_binary(candidate)
        ):
            return candidate
    return None


def resolve_nim_workspace_path(
    project_root: Path, raw_path: str | os.PathLike[str]
) -> Path:
    """Resolve a local input path and require it to stay below project root."""
    raw = os.fspath(raw_path)
    if "\x00" in raw:
        raise ValueError("Nim path contains null bytes")
    candidate = Path(raw).expanduser()
    if ".." in candidate.parts:
        raise ValueError("Nim path contains traversal components")
    root = Path(project_root).expanduser().resolve()
    resolved = (
        candidate.resolve(strict=False)
        if candidate.is_absolute()
        else (root / candidate).resolve(strict=False)
    )
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Nim path resolves outside the project workspace") from exc
    return resolved


def run_nim_process(  # noqa: C901
    args: Iterable[str | os.PathLike[str]],
    *,
    cwd: Path,
    timeout: float = 30.0,
    max_output_bytes: int = 1_048_576,
    input_text: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
) -> NimProcessResult:
    """Run a Nim bridge process with bounded output and a hard deadline.

    The runner never invokes a shell.  Reader threads continuously drain both
    pipes while retaining at most ``max_output_bytes`` per stream, preventing a
    verbose or malformed native process from deadlocking the parent.
    """
    command = [os.fspath(arg) for arg in args]
    if not command:
        raise ValueError("Nim process command cannot be empty")
    workdir = Path(cwd).expanduser().resolve()
    if not workdir.is_dir():
        raise FileNotFoundError(f"Nim process cwd does not exist: {workdir}")
    if timeout <= 0:
        raise ValueError("Nim process timeout must be positive")
    if max_output_bytes <= 0:
        raise ValueError("Nim process output limit must be positive")

    process = subprocess.Popen(
        command,
        cwd=str(workdir),
        env=env,
        stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    stdout_buffer = bytearray()
    stderr_buffer = bytearray()
    limited = {"stdout": False, "stderr": False}

    def drain(stream, buffer: bytearray, key: str) -> None:
        while True:
            chunk = stream.read(65536)
            if not chunk:
                return
            remaining = max_output_bytes - len(buffer)
            if remaining > 0:
                buffer.extend(chunk[:remaining])
            if len(chunk) > max(remaining, 0):
                limited[key] = True

    readers = [
        threading.Thread(
            target=drain,
            args=(process.stdout, stdout_buffer, "stdout"),
            daemon=True,
        ),
        threading.Thread(
            target=drain,
            args=(process.stderr, stderr_buffer, "stderr"),
            daemon=True,
        ),
    ]
    for reader in readers:
        reader.start()

    if input_text is not None and process.stdin is not None:
        try:
            process.stdin.write(input_text.encode("utf-8"))
            process.stdin.close()
        except BrokenPipeError:
            process.stdin.close()

    timed_out = False
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        process.terminate()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for reader in readers:
        reader.join(timeout=1.0)

    return NimProcessResult(
        returncode=process.returncode if process.returncode is not None else -1,
        stdout=bytes(stdout_buffer),
        stderr=bytes(stderr_buffer),
        timed_out=timed_out,
        output_limited=limited["stdout"] or limited["stderr"],
    )


def build_nim_success_payload(
    tool: str, payload: Optional[Dict[str, Any]] = None, backend: str = "nim"
) -> Dict[str, Any]:
    """Build a standardized success payload for Nim bridge tools."""
    result: Dict[str, Any] = {"ok": True, "tool": tool, "backend": backend}
    if payload:
        result.update(payload)
    return result


def build_nim_error_payload(
    tool: str,
    message: str,
    code: str,
    *,
    details: Optional[Any] = None,
    backend: str = "nim",
    payload: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a standardized error payload for Nim bridge tools."""
    result: Dict[str, Any] = {
        "ok": False,
        "tool": tool,
        "backend": backend,
        "error": message,
        "error_code": code,
    }
    if details is not None:
        result["error_details"] = details
    if payload:
        result.update(payload)
    return result
