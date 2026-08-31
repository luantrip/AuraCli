"""Testes para tool_calling."""


class TestToolCalling:
    """Testes para tool calling."""

    def test_tool_calling_imports(self):
        """Testa imports do módulo tool_calling."""
        from aura_cli.core.agents import tool_calling

        assert tool_calling is not None
