from __future__ import annotations

from pathlib import Path
import threading

import pytest

from aura_cli.core.memory import memory_manager
from aura_cli.core.memory.notebook_service import (
    NotebookService,
    _resolve_contained_path,
)


def _service(base: Path, *, enabled: bool = False, lib=None) -> NotebookService:
    service = object.__new__(NotebookService)
    service.base_path = base.resolve()
    service.session_id = "session"
    service.session_path = service.base_path / service.session_id
    service.page_counter = 1
    service._page_counter_lock = threading.Lock()
    service._nim_state_lock = threading.Lock()
    service._lib = lib
    service._nim_enabled = enabled
    service._initialized = True
    return service


def test_contained_path_accepts_documented_absolute_and_aura_relative(tmp_path):
    project = tmp_path / "project"
    base = project / ".aura" / "notebooks"
    expected = base / "session" / "pagina_001.txt"

    assert _resolve_contained_path(base, expected) == expected
    assert (
        _resolve_contained_path(base, ".aura/notebooks/session/pagina_001.txt")
        == expected
    )
    with pytest.raises(ValueError):
        _resolve_contained_path(base, tmp_path / "outside.txt")
    with pytest.raises(ValueError):
        _resolve_contained_path(base, "session/../outside.txt")
    with pytest.raises(ValueError):
        _resolve_contained_path(base, "session/\x00bad.txt")


def test_service_read_rejects_path_outside_workspace(tmp_path):
    base = tmp_path / "project" / ".aura" / "notebooks"
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    service = _service(base)
    service._use_nim = lambda: False

    result = service.read_page(str(outside), verify_integrity=False)

    assert result.startswith("ERRO:")
    assert "outside" in result.lower()


def test_service_rejects_content_over_nim_line_limit(tmp_path):
    service = _service(tmp_path / ".aura" / "notebooks")
    service._use_nim = lambda: False

    with pytest.raises(ValueError, match="1000"):
        service.write_page("\n".join("line" for _ in range(1001)))


class _FailingIndexLib:
    def notebookReadIndex(self, _path):
        return b"# Index\n"

    def notebookUpdateIndex(self, _path, _content):
        return -1


def test_service_propagates_negative_index_return(tmp_path):
    service = _service(
        tmp_path / ".aura" / "notebooks", enabled=True, lib=_FailingIndexLib()
    )
    service._use_nim = lambda: True
    service.read_index = lambda: "# Index\n"

    with pytest.raises(OSError, match="Failed to update index"):
        service._update_index(service.session_path / "pagina_001.txt", "summary")


def test_incomplete_ffi_is_rejected():
    class Function:
        argtypes = None
        restype = None

    class MissingLibrary:
        notebookGetVersion = Function()

    with pytest.raises(OSError, match="ABI incompleto"):
        memory_manager._configure_nim_library(MissingLibrary())


def test_notebook_manager_does_not_load_nim_from_worker(monkeypatch, tmp_path):
    called = []

    def forbidden_load():
        called.append(True)
        raise AssertionError("Nim load must not run in a worker")

    monkeypatch.setattr(memory_manager, "_get_nim_library", forbidden_load)
    instances = []

    def worker():
        instances.append(memory_manager.NotebookManager(str(tmp_path / "memory")))

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()

    assert not called
    assert len(instances) == 1
    assert instances[0].lib is None
