"""Aura CLI optional Nim artifacts.

This package only locates prebuilt artifacts.  The main Aura runtime performs
native-format, architecture and ABI validation before loading or executing
anything.
"""

from __future__ import annotations

import os
from pathlib import Path
import platform

__version__ = "0.1.0"

_BIN_DIR = Path(__file__).parent / "bin"
_EXECUTABLES = (
    "imagination",
    "nexus",
    "sentinel",
    "prism",
    "forge",
    "aura-monitor",
)


def get_platform_tag() -> str:
    """Return the canonical platform/architecture artifact tag."""
    system = {
        "Darwin": "macos",
        "Windows": "windows",
        "Linux": "linux",
    }.get(platform.system())
    if system is None:
        raise RuntimeError(f"Unsupported platform: {platform.system()}")
    machine = platform.machine().lower()
    arch = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "x86_64": "x86_64",
        "arm64": "aarch64",
        "aarch64": "aarch64",
    }.get(machine, machine)
    return f"{system}-{arch}"


def get_platform_bin_dir() -> Path:
    """Return the canonical directory owned by this distribution."""
    return _BIN_DIR / get_platform_tag()


def get_executable_filename(name: str, *, platform_tag: str | None = None) -> str:
    """Return the canonical executable filename for a platform tag."""
    tag = platform_tag or get_platform_tag()
    return f"{name}.exe" if tag.startswith("windows-") else name


def get_library_filename(
    name: str = "notebook", *, platform_tag: str | None = None
) -> str:
    """Return the canonical shared-library filename for a platform tag."""
    tag = platform_tag or get_platform_tag()
    base = name
    for suffix in (".so", ".dylib", ".dll"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    extension = (
        "dll"
        if tag.startswith("windows-")
        else "dylib"
        if tag.startswith("macos-")
        else "so"
    )
    return f"{base}.{extension}"


def get_bin_path(name: str) -> Path | None:
    """Get an existing canonical Nim artifact path for this platform.

    The helper does not load or execute the artifact.  Native validation is
    intentionally centralized in ``aura_cli.core.nim_runtime``.
    """
    platform_tag = get_platform_tag()
    if name == "notebook" or name.startswith("notebook."):
        filename = get_library_filename(name, platform_tag=platform_tag)
    elif name in _EXECUTABLES:
        filename = get_executable_filename(name, platform_tag=platform_tag)
    else:
        return None
    path = get_platform_bin_dir() / filename
    if not path.is_file():
        return None
    if name not in {
        "notebook",
        "notebook.so",
        "notebook.dylib",
        "notebook.dll",
    } and not os.access(path, os.X_OK):
        return None
    return path


def get_all_binaries() -> dict[str, Path | None]:
    """Get all available Nim artifacts by logical component name."""
    return {
        **{name: get_bin_path(name) for name in _EXECUTABLES},
        "notebook": get_bin_path("notebook"),
    }


def is_available() -> bool:
    """Return whether at least one canonical Nim artifact is present."""
    return any(get_all_binaries().values())
