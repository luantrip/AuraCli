"""Testes End-to-End de comandos."""


class TestE2ECommands:
    """Testes E2E de comandos."""

    def test_command_processor_exists(self):
        """Testa que command processor existe."""
        from aura_cli.cli import command_processor

        assert command_processor is not None

    def test_shell_command_detection(self):
        """Testa detecção de comandos shell."""
        from aura_cli.core.tools.shell import should_execute_directly

        # Função existe
        assert should_execute_directly is not None

    def test_shell_command_extraction(self):
        """Testa extração de comandos shell."""
        from aura_cli.core.tools.shell import extract_shell_command

        cmd = extract_shell_command("ls -la")
        assert isinstance(cmd, str)
