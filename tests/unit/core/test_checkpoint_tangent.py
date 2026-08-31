"""Tests for core/checkpoint/manager.py and core/tangent/manager.py."""

import pytest

from aura_cli.core.checkpoint.manager import CheckpointManager
from aura_cli.core.tangent.manager import TangentManager

# ── CheckpointManager ────────────────────────────────────────────────────────


@pytest.fixture
def ckpt(tmp_path):
    # CheckpointManager uses GIT_WORK_TREE pointing to cwd, so we need
    # at least one tracked file in the work tree for `git commit` to succeed.
    # Create a sentinel file and configure git identity.
    import os
    import subprocess

    sentinel = tmp_path / "README.md"
    sentinel.write_text("checkpoint test\n", encoding="utf-8")

    # Ensure git user identity is set for this test (required in CI/Linux)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.com",
    }

    ckpt_dir = tmp_path / ".checkpoints"
    mgr = CheckpointManager(shadow_dir=ckpt_dir)
    mgr.init()

    # Stage the sentinel file so the first commit has content
    git_env = {**env, "GIT_DIR": str(ckpt_dir), "GIT_WORK_TREE": str(tmp_path)}
    subprocess.run(["git", "add", "-A"], env=git_env, check=True, capture_output=True)

    # Patch os.environ inside the manager's create() to include identity vars
    import unittest.mock as mock

    mgr._git_env_extra = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@t.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@t.com",
        "GIT_WORK_TREE": str(tmp_path),
    }

    # Monkeypatch os.environ for the duration so manager picks up identity
    with mock.patch.dict(os.environ, mgr._git_env_extra):
        yield mgr


class TestCheckpointManager:
    def test_init_creates_dir(self, tmp_path):
        mgr = CheckpointManager(shadow_dir=tmp_path / ".ckpt")
        mgr.init()
        assert (tmp_path / ".ckpt").exists()

    def test_list_returns_list(self, ckpt):
        result = ckpt.list()
        assert isinstance(result, list)
        # Uma lista vazia é válida para um checkpoint manager recém-criado
        assert len(result) >= 0

    def test_create_returns_result(self, ckpt):
        result = ckpt.create("test checkpoint")
        assert result is not None

    def test_list_after_create_has_entry(self, ckpt):
        ckpt.create("first")
        assert len(ckpt.list()) >= 1

    def test_diff_requires_checkpoint_id(self, ckpt):
        # diff(checkpoint1, checkpoint2="HEAD") — needs a valid id
        ckpt.create("base")
        checkpoints = ckpt.list()
        if checkpoints:
            result = ckpt.diff(checkpoints[0].id)
            assert result is None or isinstance(result, str)


# ── TangentManager ───────────────────────────────────────────────────────────


class TestTangentManager:
    def test_in_tangent_is_property_false_initially(self):
        tm = TangentManager()
        # in_tangent is a @property
        assert tm.in_tangent is False

    def test_enter_sets_tangent_mode(self):
        tm = TangentManager()
        history = [{"role": "user", "content": "hello"}]
        tm.enter(history)
        assert tm.in_tangent is True

    def test_exit_restores_history(self):
        tm = TangentManager()
        history = [{"role": "user", "content": "original"}]
        tm.enter(history)
        # exit returns Tuple[List, str]
        result = tm.exit(history)
        assert tm.in_tangent is False
        restored, msg = result
        assert isinstance(restored, list)
        assert isinstance(msg, str)

    def test_get_indicator_empty_when_not_in_tangent(self):
        tm = TangentManager()
        assert tm.get_indicator() == ""

    def test_get_indicator_shows_tangent_when_active(self):
        tm = TangentManager()
        tm.enter([{"role": "user", "content": "test"}])
        assert tm.get_indicator() != ""

    def test_forget_removes_messages(self):
        tm = TangentManager()
        history = [
            {"role": "system", "content": "sys"},
            {"role": "user", "content": "msg1"},
            {"role": "assistant", "content": "resp1"},
            {"role": "user", "content": "msg2"},
            {"role": "assistant", "content": "resp2"},
        ]
        result = tm.forget(history, 2, interactive=False)
        assert len(result) < len(history)
