"""Testes para UIManager - Gerenciador centralizado de UI."""

from unittest.mock import patch

from rich.console import Console


def test_ui_package_exports_remain_available_lazily():
    """Package-level convenience imports must not require eager UI loading."""
    from aura_cli.cli.ui import ToolResult, UIIcons

    assert UIIcons.AURA
    assert ToolResult is not None


class TestUIManager:
    """Testes para UIManager."""

    def test_ui_manager_init(self):
        """Testa inicialização do UIManager."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()

        assert ui is not None
        assert ui.console is not None
        assert ui.stats is not None
        assert ui.display is not None
        assert ui.status is not None
        assert ui.status_bar is not None

    def test_status_bar_with_notification(self):
        """Testa StatusBar com notificação."""
        from aura_cli.cli.ui.components.status_bar import StatusBar
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        status_bar = StatusBar(stats)

        stats.set_notification("[green]Test notification[/green]", duration_seconds=1.0)

        result = status_bar.render("No Tasks")
        assert result is not None

    def test_status_bar_without_notification(self):
        """Testa StatusBar sem notificação."""
        from aura_cli.cli.ui.components.status_bar import StatusBar
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        stats.clear_notification()
        status_bar = StatusBar(stats)

        result = status_bar.render("No Tasks")
        assert result is not None

    def test_status_bar_handles_missing_model(self):
        """Modelo ausente deve aparecer como auto, sem quebrar a renderização."""
        from aura_cli.cli.ui.components.status_bar import StatusBar
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        stats.current_model = None

        result = StatusBar(stats).render("No Tasks")

        assert result is not None

    def test_ui_manager_with_custom_stats(self):
        """Testa UIManager com stats customizado."""
        from aura_cli.cli.ui.manager import UIManager
        from aura_cli.core.stats import get_stats

        custom_stats = get_stats()
        ui = UIManager(stats=custom_stats)

        assert ui.stats == custom_stats

    def test_ui_manager_uses_injected_console(self):
        """All CLI renderers should be able to share the session console."""
        from aura_cli.cli.ui.manager import UIManager

        console = Console(record=True)
        ui = UIManager(console=console)

        assert ui.console is console
        assert ui.display.console is console

    @patch("aura_cli.cli.ui.rendering.RenderCoordinator.render_response")
    def test_display_response(self, mock_render):
        """Testa exibição de resposta (delegação)."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()
        ui.display_response("Test response")

        assert mock_render.called

    @patch("aura_cli.cli.ui.rendering.RenderCoordinator.render_error")
    def test_display_error(self, mock_render):
        """Testa exibição de erro (delegação)."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()
        ui.display_error("Test error")

        assert mock_render.called

    @patch("aura_cli.cli.ui.rendering.RenderCoordinator.render_success")
    def test_display_success(self, mock_render):
        """Testa exibição de sucesso (delegação)."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()
        ui.display_success("Test success")

        assert mock_render.called

    @patch("aura_cli.cli.ui.terminal_command.display_run_terminal_command")
    def test_display_shell_output_uses_terminal_command_entrypoint(self, mock_display):
        """Shell output should flow through the canonical shell UI entrypoint."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()
        ui.display_shell_output("ls -la", True, "file1\nfile2")

        mock_display.assert_called_once()
        kwargs = mock_display.call_args.kwargs
        assert kwargs["command"] == "ls -la"
        assert kwargs["status"] == "completed"
        assert kwargs["exit_code"] == 0

    @patch("rich.console.Console.print")
    def test_print_wrapper(self, mock_print):
        """Testa wrapper de print."""
        from aura_cli.cli.ui.manager import UIManager

        ui = UIManager()
        ui.print("Test message")

        assert mock_print.called
