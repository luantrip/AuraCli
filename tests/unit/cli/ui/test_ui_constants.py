"""Testes para cli/ui/constants.py."""


class TestUIConstants:
    """Testes para constantes de UI."""

    def test_ui_icons_import(self):
        """Testa importação de UIIcons."""
        from aura_cli.cli.ui.constants import UIIcons

        assert UIIcons is not None
        assert hasattr(UIIcons, "SUCCESS")
        assert hasattr(UIIcons, "ERROR")
        assert hasattr(UIIcons, "WARNING")

    def test_ui_styles_import(self):
        """Testa importação de UIStyles."""
        from aura_cli.cli.ui.constants import UIStyles

        assert UIStyles is not None
        assert hasattr(UIStyles, "SUCCESS")
        assert hasattr(UIStyles, "ERROR")
        assert hasattr(UIStyles, "WARNING")

    def test_ui_icons_values(self):
        """Testa valores de UIIcons."""
        from aura_cli.cli.ui.constants import UIIcons

        # Verifica que os ícones são strings
        assert isinstance(UIIcons.SUCCESS, str)
        assert isinstance(UIIcons.ERROR, str)
        assert isinstance(UIIcons.WARNING, str)

    def test_ui_styles_values(self):
        """Testa valores de UIStyles."""
        from aura_cli.cli.ui.constants import UIStyles

        # Verifica que os estilos são strings usando safe_style (que sempre retorna string)
        success_style = UIStyles.safe_style("SUCCESS", "green")
        error_style = UIStyles.safe_style("ERROR", "red")
        warning_style = UIStyles.safe_style("WARNING", "yellow")
        assert isinstance(success_style, str)
        assert isinstance(error_style, str)
        assert isinstance(warning_style, str)
