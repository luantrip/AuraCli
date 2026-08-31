from __future__ import annotations

import struct

from aura_cli.core import nim_runtime


def _elf(machine: int = 0x3E) -> bytes:
    return (
        b"\x7fELF"
        + bytes([2, 1, 1, 0])
        + b"\0" * 8
        + struct.pack("<HH", 2, machine)
        + b"\0" * 32
    )


def _macho(cputype: int = 0x01000007) -> bytes:
    return b"\xcf\xfa\xed\xfe" + struct.pack("<I", cputype) + b"\0" * 32


def _pe(machine: int = 0x8664) -> bytes:
    data = bytearray(b"\0" * 128)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 64)
    data[64:68] = b"PE\0\0"
    struct.pack_into("<H", data, 68, machine)
    return bytes(data)


def test_target_and_filenames_are_canonical():
    linux = nim_runtime.parse_nim_target("linux-amd64")
    windows = nim_runtime.parse_nim_target("windows-x64")
    macos = nim_runtime.parse_nim_target("darwin-arm64")

    assert linux.tag == "linux-x86_64"
    assert windows.tag == "windows-x86_64"
    assert macos.tag == "macos-aarch64"
    assert nim_runtime.nim_executable_filename("forge", target=windows) == "forge.exe"
    assert (
        nim_runtime.nim_library_filename("notebook.so", target=windows)
        == "notebook.dll"
    )
    assert nim_runtime.nim_expected_artifacts("windows-x86_64")[-1] == "notebook.dll"


def test_native_format_requires_current_host_architecture(monkeypatch, tmp_path):
    monkeypatch.setattr(nim_runtime.sys, "platform", "linux")
    monkeypatch.setattr(nim_runtime.platform, "machine", lambda: "x86_64")
    good = tmp_path / "good"
    good.write_bytes(_elf())
    wrong_arch = tmp_path / "wrong-arch"
    wrong_arch.write_bytes(_elf(0xB7))
    script = tmp_path / "script"
    script.write_text("#!/bin/sh\n", encoding="utf-8")

    assert nim_runtime.is_compatible_native_binary(good)
    assert not nim_runtime.is_compatible_native_binary(wrong_arch)
    assert not nim_runtime.is_compatible_native_binary(script)


def test_native_format_parsers_cover_macos_and_windows(monkeypatch, tmp_path):
    mac = tmp_path / "mac"
    mac.write_bytes(_macho())
    monkeypatch.setattr(nim_runtime.sys, "platform", "darwin")
    monkeypatch.setattr(nim_runtime.platform, "machine", lambda: "x86_64")
    assert nim_runtime.is_compatible_native_binary(mac)

    win = tmp_path / "win"
    win.write_bytes(_pe())
    monkeypatch.setattr(nim_runtime.sys, "platform", "win32")
    monkeypatch.setattr(nim_runtime.platform, "machine", lambda: "AMD64")
    assert nim_runtime.is_compatible_native_binary(win)


def test_wrongly_named_configured_file_is_not_used(monkeypatch, tmp_path):
    wrong_name = tmp_path / "notebook.so"
    wrong_name.write_bytes(_elf())

    class Config:
        def get(self, key):
            assert key == "nim_binary_path"
            return str(wrong_name)

    monkeypatch.setattr(nim_runtime, "get_config_manager", lambda: Config())
    monkeypatch.setattr(nim_runtime, "platform_bin_dirs", list)
    monkeypatch.setattr(nim_runtime.shutil, "which", lambda _name: None)

    assert nim_runtime.resolve_nim_binary("forge") is None


def test_library_resolution_rejects_wrong_native_format(monkeypatch, tmp_path):
    wrong = tmp_path / "notebook.so"
    wrong.write_bytes(b"not-a-library")

    class Config:
        def get(self, key):
            assert key == "nim_binary_path"
            return str(tmp_path)

    monkeypatch.setattr(nim_runtime, "get_config_manager", lambda: Config())
    monkeypatch.setattr(nim_runtime, "platform_bin_dirs", list)

    assert nim_runtime.resolve_nim_library("notebook.so") is None
