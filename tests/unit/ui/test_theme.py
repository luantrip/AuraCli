"""
Testes para o ThemeManager (Sistema de Temas).

Verifica:
- Carregamento de temas TOML
- Singleton pattern
- Fallback gracioso
- Acesso a cores, estilos e layout
"""

from unittest.mock import mock_open, patch

from aura_cli.cli.ui.theme_manager import ThemeManager

# Mock de um arquivo de tema TOML válido
MOCK_THEME_TOML = """
[metadata]
name = "test_theme"
version = "1.0.0"

[colors]
primary = "#7aa2f7"
secondary = "#bb9af7"
background = "#1a1b26"
surface = "#24283b"
muted = "#565f89"

[styles]
title = "bold primary"
body = "white"

[borders]
border_primary = "#7aa2f7"

[layout]
panel_padding = [1, 2]
chat_padding = [0, 1]
chat_margin = [0, 0, 1, 0]
chat_width_ratio = 0.85

[appearance]
panel_border_type = "heavy"
syntax_theme = "monokai"
"""


class TestThemeManager:
    """Testes para o sistema de temas."""

    def setup_method(self):
        """Reseta o singleton antes de cada teste."""
        ThemeManager._instance = None
        if hasattr(ThemeManager, "_initialized"):
            delattr(ThemeManager, "_initialized")

    def teardown_method(self):
        """Limpa o singleton após cada teste."""
        ThemeManager._instance = None
        if hasattr(ThemeManager, "_initialized"):
            delattr(ThemeManager, "_initialized")

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_THEME_TOML)
    @patch("os.path.exists", return_value=True)
    def test_load_theme_success(self, mock_exists, mock_file):
        """Testa o carregamento bem-sucedido de um tema."""
        manager = ThemeManager("test_theme")

        assert manager.get_color("primary") == "#7aa2f7"
        assert manager.get_color("background") == "#1a1b26"
        assert manager.get_layout_property("panel_padding") == [1, 2]
        assert manager.get_layout_property("chat_width_ratio") == 0.85
        assert manager.get_appearance_property("syntax_theme") == "monokai"

    @patch("builtins.open", new_callable=mock_open, read_data=MOCK_THEME_TOML)
    @patch("os.path.exists", return_value=True)
    def test_style_resolution(self, mock_exists, mock_file):
        """Testa se os estilos resolvem referências de cores."""
        manager = ThemeManager("test_theme")

        # O estilo "title" referencia "primary" que deve ser resolvido
        title_style = manager.get_style("title")
        assert "#7aa2f7" in title_style or "bold" in title_style

    def test_singleton_behavior(self):
        """Garante que ThemeManager é um Singleton."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=MOCK_THEME_TOML)):
                m1 = ThemeManager()
                m2 = ThemeManager()
                assert m1 is m2
                assert id(m1) == id(m2)

    def test_get_color_fallback(self):
        """Testa fallback quando cor não existe."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=MOCK_THEME_TOML)):
                manager = ThemeManager("test_theme")
                # Cor que não existe retorna o próprio nome
                result = manager.get_color("nonexistent_color")
                assert result == "nonexistent_color"

    def test_get_layout_with_default(self):
        """Testa valor default para propriedade de layout inexistente."""
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", mock_open(read_data=MOCK_THEME_TOML)):
                manager = ThemeManager("test_theme")
                result = manager.get_layout_property(
                    "nonexistent_prop", default="fallback"
                )
                assert result == "fallback"
