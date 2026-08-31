"""Fake-first subprocess contracts for Nim Sentinel and Forge bridges.

Native binaries are intentionally never started by the offline unit suite.  A
separate native smoke job may exercise the compiled artifacts on its host.
"""

from __future__ import annotations

import json

from aura_cli.core.context import sentinel_manager
from aura_cli.core.quality import forge_bridge


class FakeResult:
    def __init__(self, payload: bytes, *, returncode: int = 0):
        self.stdout = payload
        self.stderr = b""
        self.returncode = returncode
        self.timed_out = False
        self.output_limited = False


def _sentinel(monkeypatch, tmp_path, payload: dict | None = None):
    monkeypatch.setattr(
        sentinel_manager.SentinelManager,
        "_find_binary",
        lambda self: tmp_path / "fake-sentinel",
    )
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        data = payload or {
            "added": ["a.py"],
            "modified": ["b.py"],
            "deleted": [],
            "stats": {"scanned": 2, "duration_ms": 1},
        }
        return FakeResult(json.dumps(data).encode())

    monkeypatch.setattr(sentinel_manager, "run_nim_process", fake_run)
    return sentinel_manager.SentinelManager(tmp_path), calls


class TestSentinelBridgeContract:
    def test_output_is_valid_json(self, monkeypatch, tmp_path):
        manager, _calls = _sentinel(monkeypatch, tmp_path)
        diff = manager.scan_changes()
        assert diff is not None
        assert isinstance(diff.to_dict(), dict)

    def test_output_has_required_keys(self, monkeypatch, tmp_path):
        manager, _calls = _sentinel(monkeypatch, tmp_path)
        data = manager.scan_changes().to_dict()
        for key in ("added", "modified", "deleted", "stats"):
            assert key in data

    def test_lists_are_arrays(self, monkeypatch, tmp_path):
        manager, _calls = _sentinel(monkeypatch, tmp_path)
        data = manager.scan_changes().to_dict()
        assert isinstance(data["added"], list)
        assert isinstance(data["modified"], list)
        assert isinstance(data["deleted"], list)

    def test_stats_has_scanned_and_duration(self, monkeypatch, tmp_path):
        manager, _calls = _sentinel(monkeypatch, tmp_path)
        stats = manager.scan_changes().stats
        assert isinstance(stats["scanned"], int)
        assert isinstance(stats["duration_ms"], int)

    def test_scan_never_constructs_version_command(self, monkeypatch, tmp_path):
        manager, calls = _sentinel(monkeypatch, tmp_path)
        assert manager.scan_changes() is not None
        assert calls and "--version" not in calls[0][0]

    def test_invalid_schema_is_rejected(self, monkeypatch, tmp_path):
        manager, _calls = _sentinel(monkeypatch, tmp_path, {"added": "not-a-list"})
        assert manager.scan_changes() is None
        assert manager.last_error


def _forge(monkeypatch, tmp_path, response: dict | bytes):
    monkeypatch.setattr(
        forge_bridge.ForgeManager,
        "_find_binary",
        lambda self: tmp_path / "fake-forge",
    )

    def fake_run(args, **kwargs):
        payload = (
            response if isinstance(response, bytes) else json.dumps(response).encode()
        )
        return FakeResult(payload)

    monkeypatch.setattr(forge_bridge, "run_nim_process", fake_run)
    return forge_bridge.ForgeManager()


class TestForgeBridgeContract:
    def test_output_is_valid_json(self, monkeypatch, tmp_path):
        manager = _forge(
            monkeypatch,
            tmp_path,
            {"success": True, "code": "x = 1", "errors": [], "logs": []},
        )
        result = manager.validate_and_fix("x=1")
        assert result.success
        assert result.code == "x = 1"

    def test_output_has_required_keys(self, monkeypatch, tmp_path):
        manager = _forge(
            monkeypatch,
            tmp_path,
            {"success": True, "code": "pass", "errors": [], "logs": []},
        )
        data = manager.validate_and_fix("pass").to_dict()
        for key in ("success", "code", "errors", "logs", "status"):
            assert key in data

    def test_valid_code_succeeds(self, monkeypatch, tmp_path):
        manager = _forge(
            monkeypatch,
            tmp_path,
            {
                "success": True,
                "code": "def hello():\n    return 42\n",
                "errors": [],
                "logs": [],
            },
        )
        assert manager.validate_and_fix("def hello():\n    return 42\n").success

    def test_syntax_error_fails(self, monkeypatch, tmp_path):
        manager = _forge(
            monkeypatch,
            tmp_path,
            {
                "success": False,
                "code": "def foo(\n    pass",
                "errors": ["SyntaxError"],
                "logs": [],
            },
        )
        result = manager.validate_and_fix("def foo(\n    pass")
        assert not result.success
        assert result.errors

    def test_fix_mode_returns_formatted_code(self, monkeypatch, tmp_path):
        manager = _forge(
            monkeypatch,
            tmp_path,
            {"success": True, "code": "x = 1 + 2", "errors": [], "logs": []},
        )
        assert manager.validate_and_fix("x=1+2", fix=True).code == "x = 1 + 2"

    def test_errors_and_logs_are_lists(self, monkeypatch, tmp_path):
        manager = _forge(
            monkeypatch,
            tmp_path,
            {"success": True, "code": "pass", "errors": [], "logs": []},
        )
        result = manager.validate_and_fix("pass")
        assert isinstance(result.errors, list)
        assert isinstance(result.logs, list)

    def test_malformed_native_json_is_an_error(self, monkeypatch, tmp_path):
        manager = _forge(monkeypatch, tmp_path, b"not json at all")
        result = manager.validate_and_fix("pass")
        assert not result.success
        assert result.status == "error"
