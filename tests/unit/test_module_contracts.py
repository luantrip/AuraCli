"""Module contract tests.

Validates that all public interfaces between subsystems remain intact.
These tests catch import breakage early without running full functionality.
"""

import os
from typing import ClassVar

import pytest


class TestToolContracts:
    """Verify TUI tools export expected interfaces."""

    def test_tools_availability_flags(self):
        from aura_cli.tui.tools import FILES_AVAILABLE, PAINT_AVAILABLE

        assert isinstance(PAINT_AVAILABLE, bool)
        assert isinstance(FILES_AVAILABLE, bool)

    def test_paint_tool_has_main(self):
        from aura_cli.tui.tools.paint.paint import main

        assert callable(main)

    def test_file_manager_exports_screen(self):
        from aura_cli.tui.tools.file_manager import FileManagerScreen

        assert FileManagerScreen is not None

    def test_monitor_exports_session(self):
        from aura_cli.tui.tools.monitor import MonitorSession

        assert MonitorSession is not None

    def test_integrations_exports_utils(self):
        from aura_cli.tui.tools.integrations import is_paint_compatible

        assert callable(is_paint_compatible)


class TestCoreContracts:
    """Verify core subsystem interfaces."""

    def test_config_exports(self):
        from aura_cli.core.config import DEFAULT_CONFIG, Config

        assert Config is not None
        assert isinstance(DEFAULT_CONFIG, dict)

    def test_llm_exports(self):
        from aura_cli.core.llm.base import query_with_fallback

        assert callable(query_with_fallback)

    def test_tools_registry(self):
        from aura_cli.core.tools.file_system import read_file, write_file

        assert callable(read_file)
        assert callable(write_file)

    def test_memory_service(self):
        from aura_cli.core.memory.memory_service import MemoryService

        assert MemoryService is not None

    def test_context_manager(self):
        from aura_cli.core.context.base import ContextManager

        assert ContextManager is not None


class TestCLIContracts:
    """Verify CLI entry points."""

    def test_app_loop_importable(self):
        from aura_cli.cli.app_loop import AppLoop

        assert AppLoop is not None

    def test_command_router_importable(self):
        from aura_cli.cli.command_router import route_command

        assert callable(route_command)

    def test_function_call_handler(self):
        from aura_cli.cli.function_call_handler import process_function_calls_loop

        assert callable(process_function_calls_loop)


class TestNimArtifactsStatic:
    """Verify Nim resolution without loading or executing native artifacts."""

    BINARIES: ClassVar[list[str]] = [
        "imagination",
        "nexus",
        "sentinel",
        "forge",
        "prism",
        "aura-monitor",
    ]

    @pytest.mark.parametrize("binary", BINARIES)
    def test_binary_resolves_from_valid_native_fixture(
        self, binary, monkeypatch, tmp_path
    ):
        from aura_cli.core import nim_runtime

        native_dir = tmp_path / nim_runtime.nim_platform_tag()
        native_dir.mkdir()

        # Build a minimal native-format stub that passes is_compatible_native_binary
        # for the current host.  ELF is only valid on Linux; macOS requires Mach-O.
        import struct
        import sys

        if sys.platform == "darwin":
            # Mach-O little-endian x86_64: magic=0xcffaedfe, cputype=0x01000007
            import platform as _platform
            machine = _platform.machine().lower()
            cputype = 0x0100000C if machine in ("arm64", "aarch64") else 0x01000007
            fake_native = (
                b"\xcf\xfa\xed\xfe"
                + struct.pack("<I", cputype)
                + b"\x00" * 16
                + b"native"
            )
        else:
            # ELF 64-bit LSB x86_64
            fake_native = (
                bytes.fromhex("7f454c46")
                + bytes([2, 1, 1, 0])
                + b"\x00" * 8
                + bytes.fromhex("02003e00")
                + b"native"
            )

        path = native_dir / binary
        path.write_bytes(fake_native)
        path.chmod(0o755)
        monkeypatch.setattr(nim_runtime, "platform_bin_dirs", lambda: [native_dir])

        resolved = nim_runtime.resolve_nim_binary(binary)

        assert resolved == path
        assert resolved.is_file()
        assert os.access(resolved, os.X_OK)

    def test_incompatible_fixture_is_rejected(self, monkeypatch, tmp_path):
        from aura_cli.core import nim_runtime

        native_dir = tmp_path / nim_runtime.nim_platform_tag()
        native_dir.mkdir()
        path = native_dir / "forge"
        path.write_bytes(b"#!/bin/sh\necho unsafe\n")
        path.chmod(0o755)
        monkeypatch.setattr(nim_runtime, "platform_bin_dirs", lambda: [native_dir])
        monkeypatch.setattr(nim_runtime.shutil, "which", lambda _name: None)

        assert nim_runtime.resolve_nim_binary("forge") is None


class TestScreenContracts:
    """Verify TUI screens import correctly."""

    def test_paint_screen(self):
        from aura_cli.tui.screens.paint_screen import PaintScreen

        assert PaintScreen is not None

    def test_monitor_screen(self):
        from aura_cli.tui.screens.monitor_screen import MonitorScreen

        assert MonitorScreen is not None

    def test_tools_menu_screen(self):
        from aura_cli.tui.screens.tools_menu_screen import ToolsMenuScreen

        assert ToolsMenuScreen is not None

    def test_file_manager_screen(self):
        from aura_cli.tui.tools.file_manager.screens import FileManagerScreen

        assert FileManagerScreen is not None
