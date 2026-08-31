from __future__ import annotations

from pathlib import Path

import pytest

from aura_cli.core import nim_runtime
from aura_cli.core.context import (
    graph_service,
    imagination_manager,
    monitor_manager,
    sentinel_manager,
)
from aura_cli.core.memory import prism_bridge
from aura_cli.core.quality import forge_bridge
from aura_cli.core.tools import nim_integration


class Result:
    def __init__(
        self,
        payload=b"{}",
        *,
        returncode=0,
        timed_out=False,
        output_limited=False,
        stderr=b"",
    ):
        self.stdout = payload
        self.stderr = stderr
        self.returncode = returncode
        self.timed_out = timed_out
        self.output_limited = output_limited


def fake_manager(cls, root: Path):
    manager = object.__new__(cls)
    manager.project_root = root.resolve()
    manager.executable_path = root / "fake-native"
    manager.last_error = None
    manager.backend = "nim"
    return manager


def test_runner_bounds_output_with_fake_popen(monkeypatch, tmp_path):
    class Stream:
        def __init__(self, data):
            self.data = data

        def read(self, _size):
            data, self.data = self.data, b""
            return data

    class Process:
        returncode = 0
        stdin = None

        def __init__(self):
            self.stdout = Stream(b"o" * 100)
            self.stderr = Stream(b"e" * 100)

        def wait(self, timeout=None):
            return None

        def terminate(self):
            self.returncode = -15

        def kill(self):
            self.returncode = -9

    monkeypatch.setattr(
        nim_runtime.subprocess, "Popen", lambda *args, **kwargs: Process()
    )

    result = nim_runtime.run_nim_process(
        ["fake-native"], cwd=tmp_path, timeout=1, max_output_bytes=10
    )

    assert result.returncode == 0
    assert result.stdout == b"o" * 10
    assert result.stderr == b"e" * 10
    assert result.output_limited


def test_imagination_bridge_uses_runner_and_rejects_escape(monkeypatch, tmp_path):
    manager = fake_manager(imagination_manager.ImaginationManager, tmp_path)
    calls = []

    def fake_run(args, **kwargs):
        calls.append((args, kwargs))
        return Result(b'{"files": []}')

    monkeypatch.setattr(imagination_manager, "run_nim_process", fake_run)
    assert manager.scan_project(".") == {"files": []}
    assert calls[0][1]["timeout"] == 60.0
    assert calls[0][1]["cwd"] == tmp_path.resolve()
    assert manager.scan_project("../outside") is None
    assert "traversal" in manager.last_error.lower()


def test_graph_service_python_fallback_is_explicit(monkeypatch, tmp_path):
    (tmp_path / "a.py").write_text("import b\n", encoding="utf-8")
    (tmp_path / "b.py").write_text("VALUE = 1\n", encoding="utf-8")
    monkeypatch.setattr(graph_service.GraphService, "_find_binary", lambda self: None)

    service = graph_service.GraphService(tmp_path)
    graph = service.build_graph()

    assert graph is not None
    assert service.backend == "python"
    assert "a.py" in graph.nodes


def test_graph_service_rejects_invalid_native_schema(monkeypatch, tmp_path):
    service = fake_manager(graph_service.GraphService, tmp_path)
    monkeypatch.setattr(
        graph_service, "run_nim_process", lambda *args, **kwargs: Result(b"[]")
    )

    def fallback():
        service.backend = "python"
        return graph_service.DependencyGraph(set(), {}, {})

    monkeypatch.setattr(service, "_python_fallback", fallback)
    graph = service.build_graph()

    assert graph is not None
    assert service.backend == "python"
    assert "json object" in service.last_error.lower()


def test_sentinel_does_not_use_version_and_validates_schema(monkeypatch, tmp_path):
    manager = fake_manager(sentinel_manager.SentinelManager, tmp_path)
    manager.state_file = tmp_path / ".aura" / "sentinel_state.json"
    calls = []

    def fake_run(args, **kwargs):
        calls.append(args)
        return Result(
            b'{"added": ["a.py"], "modified": [], "deleted": [], "stats": {"scanned": 1}}'
        )

    monkeypatch.setattr(sentinel_manager, "run_nim_process", fake_run)
    diff = manager.scan_changes()

    assert diff is not None and diff.added == ["a.py"]
    assert "--version" not in calls[0]
    assert calls[0][1:] == [str(tmp_path.resolve()), str(manager.state_file)]


def test_prism_rejects_invalid_schema(monkeypatch, tmp_path):
    source = tmp_path / "file.py"
    source.write_text("pass\n", encoding="utf-8")
    manager = fake_manager(prism_bridge.PrismManager, tmp_path)
    monkeypatch.setattr(
        prism_bridge, "run_nim_process", lambda *args, **kwargs: Result(b"{}")
    )

    assert manager.chunk_file(str(source)) == []
    assert "array" in manager.last_error.lower()


def test_monitor_rejects_unsafe_sources(tmp_path):
    manager = fake_manager(monitor_manager.MonitorManager, tmp_path)

    with pytest.raises(ValueError):
        manager._validate_source("file:///etc/passwd")
    with pytest.raises(ValueError):
        manager._validate_source("http://127.0.0.1/private")
    with pytest.raises(ValueError):
        manager._validate_source("../outside.html")
    assert (
        manager._validate_source("https://example.com/docs")
        == "https://example.com/docs"
    )


def test_forge_uses_code_key_and_explicit_status(monkeypatch, tmp_path):
    manager = fake_manager(forge_bridge.ForgeManager, tmp_path)
    monkeypatch.setattr(
        forge_bridge,
        "run_nim_process",
        lambda *args, **kwargs: Result(
            b'{"success": true, "code": "x = 1", "errors": [], "logs": []}'
        ),
    )

    result = manager.validate_and_fix("x=1")

    assert result.success
    assert result.code == "x = 1"
    assert result.status == "ok"


def test_format_file_writes_canonical_code_key(monkeypatch):
    writes = []
    monkeypatch.setattr(
        nim_integration,
        "sanitize_code",
        lambda content, fix=True: {"ok": True, "code": "x = 1"},
    )
    import aura_cli.core.tools.file_system as file_system

    monkeypatch.setattr(file_system, "read_file", lambda _path: "x=1")
    monkeypatch.setattr(
        file_system, "write_file", lambda path, content: writes.append((path, content))
    )

    result = nim_integration.format_file("file.py")

    assert result["ok"]
    assert result["changed"]
    assert writes == [("file.py", "x = 1")]


@pytest.mark.asyncio
async def test_alternative_imagination_falls_back_on_bounded_failure(
    monkeypatch, tmp_path
):
    from aura_cli.core.tools import imagination_tools

    monkeypatch.setattr(imagination_tools, "PROJECT_ROOT", tmp_path)
    scanner = imagination_tools.ImaginationScanner()
    scanner._nim_available = True
    monkeypatch.setattr(
        imagination_tools,
        "run_nim_process",
        lambda *args, **kwargs: Result(returncode=1, stderr=b"failed"),
    )
    result = await scanner.scan_async(tmp_path)

    assert result.root_path == str(tmp_path.resolve())
