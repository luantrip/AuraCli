"""CLI adapter contract for workflow tool execution."""

from unittest.mock import AsyncMock, Mock, patch

from aura_cli.cli.commands.management import _create_workflow_tool_executor


def test_cli_workflow_adapter_uses_canonical_executor() -> None:
    console = Mock()
    canonical = AsyncMock(return_value=("result", 0.1))

    with (
        patch("aura_cli.cli.tool_execution.execute_tool_call", canonical),
        patch(
            "aura_cli.core.service_registry.get_tools_dict",
            return_value={"read_file": Mock()},
        ),
        patch("aura_cli.cli.ui.manager.UIManager") as ui_manager,
        patch("aura_cli.core.stats.get_stats") as get_stats,
    ):
        execute = _create_workflow_tool_executor(console)
        result = execute("read_file", {"path": "x"}, 30)

    assert result == "result"
    canonical.assert_awaited_once()
    assert canonical.await_args.args[0:2] == ("read_file", {"path": "x"})
    ui_manager.assert_called_once_with(stats=get_stats.return_value, console=console)
