"""Tests for delegated-task follow-up panel in the TUI."""

from unittest.mock import Mock

from aura_cli.tui.widgets.delegation_panel import DelegationPanel


def test_delegation_panel_builds_snapshot_from_app_loop():
    """Panel should source delegated-task data from AppLoop methods."""
    panel = DelegationPanel()
    app_loop = Mock()
    app_loop.summarize_delegated_tasks.return_value = "delegated_total=1"
    app_loop.get_latest_delegated_task.side_effect = [
        "agi-latest",
        "ops-latest",
    ]
    app_loop.list_delegated_tasks.return_value = "task-1"
    app_loop.get_delegated_task_artifacts.return_value = "artifacts"
    panel._get_app_loop = Mock(return_value=app_loop)

    snapshot = panel._build_snapshot()

    assert snapshot.summary == "delegated_total=1"
    assert snapshot.latest_agi == "agi-latest"
    assert snapshot.latest_ops == "ops-latest"
    assert snapshot.details == "task-1"
    assert snapshot.artifacts == "artifacts"


def test_delegation_panel_reattach_prefers_latest_agi():
    """Reattach should prefer AGI when one exists."""
    panel = DelegationPanel()
    app_loop = Mock()
    app_loop.get_latest_delegated_task.side_effect = [
        "task_id=agi-1",
        "task_id=ops-1",
    ]
    app_loop.reattach_delegated_task_context.return_value = "reattached"
    panel._get_app_loop = Mock(return_value=app_loop)
    panel.query_one = Mock(return_value=Mock(update=Mock()))

    result = panel._reattach_latest()

    assert result == "reattached"
    app_loop.reattach_delegated_task_context.assert_called_once_with(agent_type="agi")


def test_delegation_panel_reattach_falls_back_to_ops():
    """Reattach should fall back to Ops when no AGI task exists."""
    panel = DelegationPanel()
    app_loop = Mock()
    app_loop.get_latest_delegated_task.side_effect = [
        "Nenhuma tarefa delegada encontrada.",
        "task_id=ops-1",
    ]
    app_loop.reattach_delegated_task_context.return_value = "reattached-ops"
    panel._get_app_loop = Mock(return_value=app_loop)
    panel.query_one = Mock(return_value=Mock(update=Mock()))

    result = panel._reattach_latest()

    assert result == "reattached-ops"
    app_loop.reattach_delegated_task_context.assert_called_once_with(agent_type="ops")


def test_delegation_panel_shows_artifacts_for_preferred_agent():
    """Artifacts should come from the preferred latest delegated task."""
    panel = DelegationPanel()
    app_loop = Mock()
    app_loop.get_latest_delegated_task.return_value = "task_id=agi-1"
    app_loop.get_delegated_task_artifacts.return_value = "artifact-list"
    update_target = Mock(update=Mock())
    panel._get_app_loop = Mock(return_value=app_loop)
    panel.query_one = Mock(return_value=update_target)

    result = panel._show_artifacts()

    assert result == "artifact-list"
    app_loop.get_delegated_task_artifacts.assert_called_once_with(agent_type="agi")


def test_delegation_panel_shows_snapshot_for_preferred_agent():
    """Snapshot should come from the preferred latest delegated task."""
    panel = DelegationPanel()
    app_loop = Mock()
    app_loop.get_latest_delegated_task.return_value = "task_id=agi-1"
    app_loop.read_delegated_task_snapshot.return_value = "snapshot-body"
    update_target = Mock(update=Mock())
    panel._get_app_loop = Mock(return_value=app_loop)
    panel.query_one = Mock(return_value=update_target)

    result = panel._show_snapshot()

    assert result == "snapshot-body"
    app_loop.read_delegated_task_snapshot.assert_called_once_with(agent_type="agi")
