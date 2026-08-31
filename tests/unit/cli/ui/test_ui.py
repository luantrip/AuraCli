"""
Testes Unitários para Módulos UI do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes de interface do usuário, incluindo constantes (ícones, estilos,
mensagens), sistema de status de ferramentas e parser ANSI para renderização.
"""

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.tool_status import (
    format_tool_status_message,
    get_status_color,
    get_status_icon,
)

# ansi_parser foi removido (código morto — render_ansi_output nunca chamado em produção)


class TestUIConstants:
    """Testes para constantes UI."""

    def test_ui_icons(self):
        """Testa ícones UI."""
        assert UIIcons.TOOL is not None
        assert UIIcons.SUCCESS is not None
        assert UIIcons.ERROR is not None

    def test_ui_styles(self):
        """Testa estilos UI."""
        assert UIStyles.safe_style("PRIMARY", "cyan") is not None
        assert UIStyles.safe_style("SUCCESS", "green") is not None
        assert UIStyles.safe_style("ERROR", "red") is not None


class TestToolStatus:
    """Testes para status de ferramentas."""

    def test_get_status_icon(self):
        """Testa obtenção de ícone de status."""
        icon = get_status_icon("done")
        assert icon is not None
        assert isinstance(icon, str)

    def test_get_status_color(self):
        """Testa obtenção de cor de status."""
        color = get_status_color("done")
        assert color is None or isinstance(color, str)

    def test_format_tool_status_message(self):
        """Testa formatação de mensagem de status."""
        msg = format_tool_status_message("read_file", "calling")
        assert "read_file" in msg.lower()
        assert isinstance(msg, str)


# TestANSIParser removido: ansi_parser.py foi deletado (código morto —
# render_ansi_output/parse_ansi_code nunca chamados em produção).
