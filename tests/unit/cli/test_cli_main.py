"""Testes para cli/main.py."""


class TestMain:
    """Testes para main.py."""

    def test_main_module_imports(self):
        """Testa que o módulo main pode ser importado."""
        from aura_cli.cli.main import _main_callback

        assert _main_callback is not None
