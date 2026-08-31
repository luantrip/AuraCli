"""Additional scenario tests for command_router behavior."""

from unittest.mock import Mock, patch

from aura_cli.cli.command_router import route_command


class TestCommandRouterScenarios:
    """Scenario coverage for config-aware shell routing."""

    def test_route_command_blocks_shell_when_disabled_in_config(self):
        """Shell command should be blocked when enable_shell is false."""
        stats = Mock()
        ui = Mock()
        ui.status_queue = Mock()
        console = Mock()

        with (
            patch(
                "aura_cli.cli.command_router.should_execute_directly", return_value=True
            ),
            patch(
                "aura_cli.cli.command_router.shell_execution_status",
                return_value=(False, "Execução de shell desabilitada."),
            ),
            patch("aura_cli.cli.command_router.execute_shell_command") as exec_shell,
        ):
            should_continue, message, *_ = route_command(
                command="ls -la",
                agi_thread=None,
                ops_thread=None,
                current_model="auto",
                stats=stats,
                ui=ui,
                console=console,
            )

        assert should_continue is True
        assert "Execução de shell desabilitada" in message
        exec_shell.assert_not_called()
