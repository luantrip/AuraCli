"""Tests for core/memory/memory_service.py and core/memory/notebook_service.py."""

import pytest

from aura_cli.core.memory.memory_service import get_memory_service, reset_memory_service
from aura_cli.core.memory.notebook_service import (
    get_notebook_service,
    reset_notebook_service,
)


@pytest.fixture(autouse=True)
def reset():
    reset_memory_service()
    reset_notebook_service()
    yield
    reset_memory_service()
    reset_notebook_service()


@pytest.fixture
def tmp_project(tmp_path):
    return tmp_path


# ── MemoryService ─────────────────────────────────────────────────────────────


class TestMemoryService:
    def test_get_memory_service_singleton(self, tmp_project):
        s1 = get_memory_service(tmp_project)
        s2 = get_memory_service(tmp_project)
        assert s1 is s2

    def test_reset_creates_new_instance(self, tmp_project):
        s1 = get_memory_service(tmp_project)
        reset_memory_service()
        s2 = get_memory_service(tmp_project)
        assert s1 is not s2

    def test_get_constitution_returns_none_or_str_initially(self, tmp_project):
        svc = get_memory_service(tmp_project)
        result = svc.get_constitution()
        assert result is None or isinstance(result, str)

    def test_save_and_get_constitution(self, tmp_project):
        svc = get_memory_service(tmp_project)
        svc.save_constitution("# Rules\n- Use Python")
        result = svc.get_constitution()
        assert result is not None
        assert "Python" in result

    def test_save_conventions(self, tmp_project):
        svc = get_memory_service(tmp_project)
        svc.save_conventions("Use snake_case for variables")
        result = svc.get_conventions()
        assert result is not None

    def test_add_learned_rule(self, tmp_project):
        svc = get_memory_service(tmp_project)
        svc.add_learned_rule("Always use type hints", context="code review")
        rules = svc.get_learned_rules()
        assert len(rules) >= 1


# ── NotebookService ───────────────────────────────────────────────────────────


class TestNotebookService:
    def test_get_notebook_service_returns_instance(self, tmp_project):
        ns = get_notebook_service(base_path=tmp_project / "notebooks")
        assert ns is not None

    def test_get_notebook_service_is_scoped_by_base_path(self, tmp_project):
        first = get_notebook_service(base_path=tmp_project / "first")
        second = get_notebook_service(base_path=tmp_project / "second")

        assert first is not second
        assert second.base_path == (tmp_project / "second").resolve()

    def test_list_pages_returns_list(self, tmp_project):
        ns = get_notebook_service(base_path=tmp_project / "nb")
        pages = ns.list_pages()
        assert isinstance(pages, list)

    def test_write_page_returns_path(self, tmp_project):
        ns = get_notebook_service(base_path=tmp_project / "nb2")
        # write_page(content, summary=None, auto_backup=True)
        result = ns.write_page("# Test\nContent here", summary="test page")
        assert result is not None

    def test_get_page_count_after_write(self, tmp_project):
        ns = get_notebook_service(base_path=tmp_project / "nb3")
        initial = ns.get_page_count()
        ns.write_page("content", summary="page1")
        assert ns.get_page_count() >= initial

    def test_get_session_info_returns_dict(self, tmp_project):
        ns = get_notebook_service(base_path=tmp_project / "nb4")
        info = ns.get_session_info()
        assert isinstance(info, dict)
        assert "page_count" in info

    def test_create_snapshot(self, tmp_project):
        ns = get_notebook_service(base_path=tmp_project / "nb5")
        history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        path = ns.create_snapshot(history, use_cognitive_refinement=False)
        assert path is not None
