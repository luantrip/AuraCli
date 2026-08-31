"""Validate a staged Aura Nim release and its package mirror."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
from pathlib import Path
import stat
import struct
import sys

from aura_cli.core.nim_runtime import run_nim_process

EXECUTABLES = (
    "imagination",
    "nexus",
    "sentinel",
    "prism",
    "forge",
    "aura-monitor",
)
LIBRARY_EXTENSIONS = {"linux": "so", "macos": "dylib", "windows": "dll"}
ARCH_ALIASES = {
    "amd64": "x86_64",
    "x64": "x86_64",
    "x86_64": "x86_64",
    "arm64": "aarch64",
    "aarch64": "aarch64",
}
ELF_MACHINES = {"x86_64": 0x3E, "aarch64": 0xB7}
MACHO_CPUS = {"x86_64": 0x01000007, "aarch64": 0x0100000C}
PE_MACHINES = {"x86_64": 0x8664, "aarch64": 0xAA64}
MAGIC = {
    "linux": (b"\x7fELF",),
    "macos": (
        b"\xcf\xfa\xed\xfe",
        b"\xfe\xed\xfa\xcf",
        b"\xca\xfe\xba\xbe",
        b"\xbe\xba\xfe\xca",
    ),
    "windows": (b"MZ",),
}
NOTEBOOK_SYMBOLS = (
    "notebookGetVersion",
    "notebookInit",
    "notebookWritePage",
    "notebookReadPage",
    "notebookListPages",
    "notebookGetPageCount",
    "notebookUpdateIndex",
    "notebookReadIndex",
    "notebookDeletePage",
    "notebookGetSessionInfo",
)


def _canonical_tag(tag: str) -> str:
    """Normalize platform/architecture aliases to the on-disk tag."""
    try:
        platform_name, architecture = tag.strip().lower().split("-", 1)
    except ValueError as exc:
        raise ValueError(f"invalid platform tag: {tag}") from exc
    platform_name = {"darwin": "macos", "win32": "windows"}.get(
        platform_name, platform_name
    )
    architecture = ARCH_ALIASES.get(architecture, architecture)
    if platform_name not in LIBRARY_EXTENSIONS:
        raise ValueError(f"unsupported platform tag: {tag}")
    if architecture not in ARCH_ALIASES.values():
        raise ValueError(f"unsupported architecture in tag: {tag}")
    return f"{platform_name}-{architecture}"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expected_names(tag: str) -> tuple[str, ...]:
    canonical = _canonical_tag(tag)
    platform_name = canonical.split("-", 1)[0]
    extension = LIBRARY_EXTENSIONS[platform_name]
    suffix = ".exe" if platform_name == "windows" else ""
    return (
        *(f"{name}{suffix}" for name in EXECUTABLES),
        f"notebook.{extension}",
    )


def _read_prefix(path: Path, size: int = 4096) -> bytes:
    try:
        with path.open("rb") as handle:
            return handle.read(size)
    except OSError:
        return b""


def _matches_architecture(data: bytes, platform_name: str, architecture: str) -> bool:
    if platform_name == "linux":
        if len(data) < 20 or data[:4] != b"\x7fELF" or data[4] != 2:
            return False
        endian = "<" if data[5] == 1 else ">" if data[5] == 2 else ""
        return (
            bool(endian)
            and struct.unpack_from(f"{endian}H", data, 18)[0]
            == ELF_MACHINES[architecture]
        )
    if platform_name == "windows":
        if len(data) < 64 or data[:2] != b"MZ":
            return False
        pe_offset = struct.unpack_from("<I", data, 0x3C)[0]
        return (
            pe_offset + 6 <= len(data)
            and data[pe_offset : pe_offset + 4] == b"PE\0\0"
            and struct.unpack_from("<H", data, pe_offset + 4)[0]
            == PE_MACHINES[architecture]
        )
    if len(data) < 8:
        return False
    expected = MACHO_CPUS[architecture]
    magic = data[:4]
    if magic in {b"\xcf\xfa\xed\xfe", b"\xfe\xed\xfa\xcf"}:
        endian = "<" if magic == b"\xcf\xfa\xed\xfe" else ">"
        return struct.unpack_from(f"{endian}I", data, 4)[0] == expected
    if magic not in {b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca"}:
        return False
    endian = ">" if magic == b"\xca\xfe\xba\xbe" else "<"
    count = struct.unpack_from(f"{endian}I", data, 4)[0]
    offset = 8
    for _ in range(min(count, 64)):
        if offset + 20 > len(data):
            break
        if struct.unpack_from(f"{endian}I", data, offset)[0] == expected:
            return True
        offset += 20
    return False


def _verify_artifact(
    source: Path,
    mirror: Path,
    *,
    platform_name: str,
    architecture: str,
    executable: bool,
) -> list[str]:
    if not source.is_file():
        return [f"missing staging artifact: {source}"]
    if not mirror.is_file():
        return [f"missing package artifact: {mirror}"]
    errors: list[str] = []
    if _digest(source) != _digest(mirror):
        errors.append(f"package mirror differs: {source.name}")
    data = _read_prefix(source)
    if not any(data.startswith(prefix) for prefix in MAGIC[platform_name]):
        errors.append(f"wrong native format for {platform_name}: {source.name}")
    elif not _matches_architecture(data, platform_name, architecture):
        errors.append(
            f"wrong architecture for {platform_name}-{architecture}: {source.name}"
        )
    mode = source.stat().st_mode
    if executable and not mode & stat.S_IXUSR:
        errors.append(f"executable bit missing: {source}")
    if not executable and mode & stat.S_IXUSR:
        errors.append(f"shared library must not be executable: {source}")
    return errors


def _verify_no_extras(directory: Path, expected: tuple[str, ...]) -> list[str]:
    if not directory.is_dir():
        return []
    allowed = set(expected) | {"SHA256SUMS"}
    return [
        f"unexpected artifact in {directory}: {path.name}"
        for path in sorted(directory.iterdir())
        if path.is_file() and path.name not in allowed
    ]


def _verify_manifests(
    directories: tuple[Path, Path], manifest: str, *, write_manifest: bool
) -> list[str]:
    errors: list[str] = []
    for directory in directories:
        manifest_path = directory / "SHA256SUMS"
        if write_manifest:
            manifest_path.write_text(manifest, encoding="utf-8")
        elif not manifest_path.is_file():
            errors.append(f"missing checksum manifest: {manifest_path}")
        elif manifest_path.read_text(encoding="utf-8") != manifest:
            errors.append(f"stale checksum manifest: {manifest_path}")
    return errors


def _host_platform() -> str:
    """Return the canonical platform name for the current runner."""
    if sys.platform.startswith("linux"):
        return "linux"
    if sys.platform.startswith("darwin"):
        return "macos"
    if sys.platform.startswith("win"):
        return "windows"
    return sys.platform


def _smoke_supported(platform_name: str) -> bool:
    """Return whether native smoke execution is safe on this host."""
    return _host_platform() == platform_name


def _smoke(staging: Path, names: tuple[str, ...]) -> list[str]:
    errors: list[str] = []
    for name in names[:-1]:
        if name.startswith("sentinel"):
            continue
        try:
            result = run_nim_process(
                [str(staging / name), "--version"],
                cwd=staging,
                timeout=5.0,
                max_output_bytes=64 * 1024,
            )
            if result.timed_out:
                errors.append(f"entrypoint smoke failed for {name}: timeout")
            elif result.output_limited:
                errors.append(f"entrypoint smoke failed for {name}: output limit")
            elif result.returncode != 0:
                stderr = result.stderr.decode(errors="replace").strip()[:160]
                errors.append(
                    f"entrypoint smoke failed for {name}: exit {result.returncode}"
                    + (f" ({stderr})" if stderr else "")
                )
        except OSError as exc:
            errors.append(f"entrypoint smoke failed for {name}: {exc}")
    try:
        library = ctypes.CDLL(str((staging / names[-1]).resolve()))
        missing = [
            symbol for symbol in NOTEBOOK_SYMBOLS if not hasattr(library, symbol)
        ]
        if missing:
            errors.append(
                "notebook loader smoke missing symbols: " + ", ".join(missing)
            )
    except OSError as exc:
        errors.append(f"notebook loader smoke failed: {exc}")
    return errors


def verify(
    root: Path,
    tag: str,
    *,
    write_manifest: bool = False,
    smoke: bool = False,
) -> list[str]:
    canonical = _canonical_tag(tag)
    staging = root / "bin" / canonical
    packaged = root / "packages" / "aura-cli-nim" / "aura_cli_nim" / "bin" / canonical
    errors: list[str] = []
    names = _expected_names(canonical)
    platform_name, architecture = canonical.split("-", 1)

    errors.extend(_verify_no_extras(staging, names))
    errors.extend(_verify_no_extras(packaged, names))
    for index, name in enumerate(names):
        errors.extend(
            _verify_artifact(
                staging / name,
                packaged / name,
                platform_name=platform_name,
                architecture=architecture,
                executable=index < len(names) - 1,
            )
        )

    if errors:
        return errors

    lines = [f"{_digest(staging / name)}  {name}" for name in names]
    manifest = "\n".join(lines) + "\n"
    errors.extend(
        _verify_manifests((staging, packaged), manifest, write_manifest=write_manifest)
    )
    if smoke and _smoke_supported(platform_name):
        errors.extend(_smoke(staging, names))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("tag", help="canonical tag, for example macos-x86_64")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    try:
        errors = verify(
            args.root,
            args.tag,
            write_manifest=args.write_manifest,
            smoke=args.smoke,
        )
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    canonical = _canonical_tag(args.tag)
    if args.smoke and not _smoke_supported(canonical.split("-", 1)[0]):
        print(
            f"WARNING: native smoke skipped for {canonical}; "
            f"runner platform is {_host_platform()}"
        )
    print(f"Nim release verified: {canonical}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
