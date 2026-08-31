"""Tests for workspace-bounded Git postconditions."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from aura_cli.cli.tool_execution import _collect_postconditions


def _success_result(stdout: str) -> SimpleNamespace:
    return SimpleNamespace(returncode=0, stdout=stdout)


def test_postconditions_default_to_canonical_workspace():
    outcome = SimpleNamespace(blocked=False)
    with (
        patch(
            "aura_cli.core.tools.file_system.get_allowed_base_dir",
            return_value=Path("/workspace"),
        ),
        patch(
            "aura_cli.cli.tool_execution.subprocess.run",
            side_effect=[
                _success_result("/workspace\n"),
                _success_result("main\n"),
                _success_result("abc123\n"),
            ],
        ) as mock_run,
    ):
        result = _collect_postconditions(
            "run_shell_command",
            {"command": "git commit -m done"},
            outcome,
        )

    assert result == {
        "repository": "/workspace",
        "branch": "main",
        "commit": "abc123",
    }
    assert all(
        call.args[0][0:3] == ["git", "-C", "/workspace"]
        for call in mock_run.call_args_list
    )


def test_postconditions_reject_external_repo_without_running_git():
    outcome = SimpleNamespace(blocked=False)
    with (
        patch(
            "aura_cli.core.tools.file_system.get_allowed_base_dir",
            return_value=Path("/workspace"),
        ),
        patch("aura_cli.cli.tool_execution.subprocess.run") as mock_run,
    ):
        result = _collect_postconditions(
            "git_commit",
            {"repo_path": "/outside/repository"},
            outcome,
        )

    assert result == {}
    mock_run.assert_not_called()


def test_postconditions_use_parent_when_path_is_a_file(tmp_path):
    file_path = tmp_path / "repo" / "tracked.txt"
    file_path.parent.mkdir()
    file_path.write_text("content", encoding="utf-8")
    outcome = SimpleNamespace(blocked=False)
    with (
        patch(
            "aura_cli.core.tools.file_system.get_allowed_base_dir",
            return_value=tmp_path,
        ),
        patch(
            "aura_cli.cli.tool_execution.subprocess.run",
            side_effect=[
                _success_result(f"{file_path.parent}\n"),
                _success_result("main\n"),
                _success_result("def456\n"),
            ],
        ) as mock_run,
    ):
        result = _collect_postconditions(
            "git_commit",
            {"path": str(file_path)},
            outcome,
        )

    assert result["repository"] == str(file_path.parent)
    assert mock_run.call_args_list[0].args[0][2] == str(file_path.parent)
