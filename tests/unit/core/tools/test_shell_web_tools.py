"""Testes para shell e web tools."""


class TestShellTools:
    """Testes para shell tools."""

    def test_shell_module_imports(self):
        """Testa imports do módulo shell."""
        from aura_cli.core.tools import shell

        assert shell is not None


class TestWebTools:
    """Testes para web tools."""

    def test_web_module_imports(self):
        """Testa imports do módulo web."""
        from aura_cli.core.tools import web

        assert web is not None
