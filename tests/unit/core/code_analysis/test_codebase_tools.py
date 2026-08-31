"""Testes para codebase_tools.py."""


class TestCodebaseTools:
    """Testes para codebase_tools."""

    def test_codebase_tools_imports(self):
        """Testa que o módulo pode ser importado."""
        from aura_cli.core.tools import codebase_tools

        assert codebase_tools is not None
