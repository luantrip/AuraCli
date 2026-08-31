from __future__ import annotations

from pathlib import Path
import sys

from aura_cli.core import nim_runtime


def test_release_package_precedes_repository_staging(monkeypatch, tmp_path):
    package_dir = tmp_path / "package"
    monkeypatch.setattr(nim_runtime, "_PROJECT_ROOT", tmp_path / "repository")
    monkeypatch.setattr(
        "aura_cli_nim.get_platform_bin_dir", lambda: package_dir, raising=False
    )

    assert nim_runtime.platform_bin_dirs()[0] == package_dir


def test_release_verifier_accepts_complete_mirrored_platform(tmp_path):
    from scripts.verify_nim_release import _expected_names, verify

    tag = "linux-x86_64"
    staging = tmp_path / "bin" / tag
    packaged = tmp_path / "packages" / "aura-cli-nim" / "aura_cli_nim" / "bin" / tag
    staging.mkdir(parents=True)
    packaged.mkdir(parents=True)
    for name in _expected_names(tag):
        payload = (
            b"\x7fELF"
            + bytes([2, 1, 1, 0])
            + b"\0" * 8
            + b"\x02\x00\x3e\x00"
            + name.encode()
        )
        for directory in (staging, packaged):
            path = directory / name
            path.write_bytes(payload)
            path.chmod(0o644 if name.startswith("notebook.") else 0o755)

    assert verify(tmp_path, tag, write_manifest=True) == []
    assert verify(tmp_path, tag) == []


def test_release_verifier_skips_incompatible_cross_target_smoke(monkeypatch, tmp_path):
    from scripts.verify_nim_release import _expected_names, verify

    tag = "macos-x86_64"
    staging = tmp_path / "bin" / tag
    packaged = tmp_path / "packages" / "aura-cli-nim" / "aura_cli_nim" / "bin" / tag
    staging.mkdir(parents=True)
    packaged.mkdir(parents=True)
    for name in _expected_names(tag):
        payload = b"\xcf\xfa\xed\xfe\x07\x00\x00\x01" + b"\0" * 16 + name.encode()
        for directory in (staging, packaged):
            path = directory / name
            path.write_bytes(payload)
            path.chmod(0o644 if name.startswith("notebook.") else 0o755)

    monkeypatch.setattr(sys, "platform", "linux")
    assert verify(tmp_path, tag, write_manifest=True, smoke=True) == []


def test_release_verifier_rejects_incomplete_platform(tmp_path):
    from scripts.verify_nim_release import verify

    errors = verify(tmp_path, "macos-x86_64")

    assert any("missing staging artifact" in error for error in errors)


def test_expected_names_use_windows_extensions():
    from scripts.verify_nim_release import _expected_names

    names = _expected_names("windows-x86_64")
    assert names[-1] == "notebook.dll"
    assert names[:-1] == tuple(
        f"{name}.exe"
        for name in (
            "imagination",
            "nexus",
            "sentinel",
            "prism",
            "forge",
            "aura-monitor",
        )
    )


def test_auxiliary_package_platform_helper_matches_runtime(monkeypatch):
    import aura_cli_nim

    monkeypatch.setattr(nim_runtime.sys, "platform", "linux")
    monkeypatch.setattr(nim_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(aura_cli_nim.platform, "system", lambda: "Linux")
    monkeypatch.setattr(aura_cli_nim.platform, "machine", lambda: "x86_64")

    assert aura_cli_nim.get_platform_tag() == nim_runtime.nim_platform_tag()
    assert (
        aura_cli_nim.get_executable_filename("forge", platform_tag="windows-x86_64")
        == "forge.exe"
    )
    assert (
        aura_cli_nim.get_library_filename(platform_tag="windows-x86_64")
        == "notebook.dll"
    )


def test_integrity_checker_is_static_only(monkeypatch, tmp_path):
    from unittest.mock import patch

    from aura_cli.core import nim_integrity

    platform_dir = tmp_path / "linux-x86_64"
    platform_dir.mkdir()
    fake_elf = (
        bytes.fromhex("7f454c46")
        + bytes([2, 1, 1, 0])
        + b"0" * 8
        + bytes.fromhex("02003e00")
        + b"native"
    )
    for name in nim_runtime.nim_expected_artifacts("linux-x86_64"):
        path = platform_dir / name
        path.write_bytes(fake_elf)
        path.chmod(0o644 if name == "notebook.so" else 0o755)
    monkeypatch.setattr(nim_integrity, "_BIN_DIR", platform_dir)
    monkeypatch.setattr(nim_integrity, "_LIBRARY", "notebook.so")

    # The integrity checker validates native format against the current host.
    # This test uses a Linux/ELF fixture explicitly to verify static-only
    # behaviour (no execution), so we stub the format check to isolate the
    # logic under test from the host platform.
    with patch(
        "aura_cli.core.nim_integrity.is_compatible_native_binary", return_value=True
    ):
        report = nim_integrity.check_nim_integrity()

    assert report.all_ok
    assert all(item.smoke_ok for item in report.binaries)


def test_build_script_rejects_unknown_target_without_skip():
    script = Path("scripts/build_nim.sh").read_text(encoding="utf-8")
    assert '*) echo "❌ Unknown Nim target: $TARGET"; exit 1 ;;' in script
    assert 'echo "  ❌ Unknown target: $t"' in script
