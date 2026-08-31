"""Tests for core/sessions/session_state.py — SessionStateManager."""

import pytest

from aura_cli.core.sessions.session_state import (
    get_session_state,
    reset_session_state,
)


@pytest.fixture(autouse=True)
def reset():
    reset_session_state()
    yield
    reset_session_state()


@pytest.fixture
def tmp_project(tmp_path):
    return tmp_path


class TestSessionStateManager:
    def test_get_session_state_singleton(self):
        s1 = get_session_state()
        s2 = get_session_state()
        assert s1 is s2

    def test_initialize(self, tmp_project):
        mgr = get_session_state()
        mgr.initialize(tmp_project)
        assert mgr.is_initialized()

    def test_get_current_state_after_init(self, tmp_project):
        mgr = get_session_state()
        mgr.initialize(tmp_project)
        state = mgr.get_current_state()
        assert state is not None

    def test_not_initialized_before_init(self):
        mgr = get_session_state()
        assert not mgr.is_initialized()

    def test_update_constitution(self, tmp_project):
        mgr = get_session_state()
        mgr.initialize(tmp_project)
        mgr.update_constitution("# Project Rules\n- Use Python 3.11")
        state = mgr.get_current_state()
        assert state.constitution is not None
        assert "Python" in state.constitution

    def test_get_constitution_returns_none_initially(self, tmp_project):
        mgr = get_session_state()
        mgr.initialize(tmp_project)
        result = mgr.get_constitution()
        # Returns None or empty string when no constitution set
        assert result is None or result == ""

    def test_get_constitution_after_update(self, tmp_project):
        mgr = get_session_state()
        mgr.initialize(tmp_project)
        mgr.update_constitution("# Constitution")
        result = mgr.get_constitution()
        assert result is not None
        assert "Constitution" in result

    def test_set_active_mode(self, tmp_project):
        mgr = get_session_state()
        mgr.initialize(tmp_project)
        mgr.set_active_mode("agi")
        state = mgr.get_current_state()
        assert state.active_mode == "agi"

    def test_ensure_initialized_after_init(self, tmp_project):
        mgr = get_session_state()
        mgr.initialize(tmp_project)
        # Após inicializar, ensure_initialized não deve lançar exceção
        # e o estado deve indicar que está inicializado
        mgr.ensure_initialized()
        assert mgr.is_initialized(), "Session state deve estar inicializado após initialize()"
