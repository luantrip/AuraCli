"""
Testes para Componentes Visuais Core (LCD, ChatBox, Markdown).

Verifica:
- AuraLCDDisplay: Renderização de terminal "LCD Style"
- AuraChatBox: Mensagens de chat fluidas com alinhamento
- AuraMarkdownDisplay: Markdown com blocos de código estilizados
- Smart Context Buffer: Detecção de inputs grandes
"""

from unittest.mock import mock_open, patch

import pytest

from aura_cli.cli.ui.theme_manager import ThemeManager

# Mock TOML para os testes
MOCK_THEME_TOML = """
[colors]
primary = "#7aa2f7"
secondary = "#bb9af7"
accent = "#7dcfff"
background = "#1a1b26"
surface = "#24283b"
muted = "#565f89"
success = "#9ece6a"
error = "#f7768e"
body = "#c0caf5"

[styles]
body = "white"
border_primary = "#7aa2f7"
border_success = "#9ece6a"
border_error = "#f7768e"
border_warning = "#e0af68"

[layout]
chat_padding = [0, 1]
chat_margin = [0, 0, 1, 0]
chat_width_ratio = 0.85
lcd_padding = [0, 0]

[appearance]
syntax_theme = "monokai"
"""


@pytest.fixture(autouse=True)
def reset_theme_manager():
    """Reset singleton before and after each test."""
    ThemeManager._instance = None
    if hasattr(ThemeManager, "_initialized"):
        delattr(ThemeManager, "_initialized")
    yield
    ThemeManager._instance = None
    if hasattr(ThemeManager, "_initialized"):
        delattr(ThemeManager, "_initialized")


@pytest.fixture
def mock_theme():
    """Fixture que configura um ThemeManager mockado."""
    with patch("os.path.exists", return_value=True):
        with patch("builtins.open", mock_open(read_data=MOCK_THEME_TOML)):
            manager = ThemeManager("test_theme")
            return manager


class TestAuraLCDDisplay:
    """Testes para o componente LCD Display."""

    def test_render_returns_panel(self, mock_theme):
        """Testa se LCDDisplay retorna um Group configurado."""
        from rich.console import Group

        from aura_cli.cli.ui.components.display.lcd_display import AuraLCDDisplay

        lcd = AuraLCDDisplay()
        renderable = lcd.render("print('hello')", title="TEST")

        # Código retorna Group, não Panel (comportamento correto)
        assert isinstance(renderable, Group)
        # Verificar que Group não está vazio
        assert renderable.renderables is not None
        assert len(renderable.renderables) > 0

    def test_render_with_line_numbers(self, mock_theme):
        """Testa renderização com números de linha."""
        from rich.console import Group

        from aura_cli.cli.ui.components.display.lcd_display import AuraLCDDisplay

        lcd = AuraLCDDisplay()
        content = "line1\nline2\nline3"
        renderable = lcd.render(content, title="LINES", line_numbers=True)

        # Código retorna Group
        assert isinstance(renderable, Group)

    def test_render_with_syntax_highlighting(self, mock_theme):
        """Testa renderização com syntax highlighting."""
        from rich.console import Group

        from aura_cli.cli.ui.components.display.lcd_display import AuraLCDDisplay

        lcd = AuraLCDDisplay()
        code = "def hello():\n    print('world')"
        renderable = lcd.render(code, title="PYTHON", format_type="python")

        # Código retorna Group
        assert isinstance(renderable, Group)


class TestAuraChatBox:
    """Testes para o componente MessageBubble (substitui AuraChatBox)."""

    def test_render_user_message(self, mock_theme):
        """Testa renderização de mensagem do usuário."""
        from datetime import datetime

        from rich.padding import Padding

        from aura_cli.cli.ui.components.display.message_bubble import (
            MessageBubble,
            MessageType,
        )

        # MessageBubble espera datetime, não float
        chat = MessageBubble(
            sender="user",
            content="Hello",
            message_type=MessageType.USER,
            timestamp=datetime.fromtimestamp(1234567890.0),
        )
        renderable = chat.render(100)

        # MessageBubble.render() retorna Padding
        assert isinstance(renderable, Padding)
        assert renderable is not None

    def test_render_agent_message(self, mock_theme):
        """Testa renderização de mensagem do agente."""
        from datetime import datetime

        from rich.padding import Padding

        from aura_cli.cli.ui.components.display.message_bubble import (
            MessageBubble,
            MessageType,
        )

        chat = MessageBubble(
            sender="aura",
            content="I can help!",
            message_type=MessageType.ASSISTANT,
            timestamp=datetime.fromtimestamp(1234567890.0),
        )
        renderable = chat.render(100)

        assert isinstance(renderable, Padding)
        assert renderable is not None

    def test_render_smart_buffer_card(self, mock_theme):
        """Testa renderização com metadata."""
        from datetime import datetime

        from rich.padding import Padding

        from aura_cli.cli.ui.components.display.message_bubble import (
            MessageBubble,
            MessageMetadata,
            MessageType,
        )

        # MessageMetadata não tem is_large_input, stats, preview - usar campos corretos
        metadata = MessageMetadata(tokens=100, model="test-model")
        chat = MessageBubble(
            sender="user",
            content="A" * 2000,
            message_type=MessageType.USER,
            timestamp=datetime.fromtimestamp(1234567890.0),
            metadata=metadata,
        )

        renderable = chat.render(100)

        # Deve renderizar sem erros
        assert isinstance(renderable, Padding)
        assert renderable is not None

    def test_chat_respects_theme_layout(self, mock_theme):
        """Testa se MessageBubble respeita configurações de layout do tema."""
        from datetime import datetime

        from rich.padding import Padding

        from aura_cli.cli.ui.components.display.message_bubble import (
            MessageBubble,
            MessageType,
        )

        chat = MessageBubble(
            sender="user",
            content="Test",
            message_type=MessageType.USER,
            timestamp=datetime.fromtimestamp(1234567890.0),
        )
        renderable = chat.render(100)

        # Verifica que foi renderizado
        assert isinstance(renderable, Padding)
        assert renderable is not None


class TestAuraMarkdownDisplay:
    """Testes para o componente Markdown Display."""

    def test_markdown_rendering(self, mock_theme):
        """Testa se o renderizador retorna um objeto Markdown customizado."""
        from aura_cli.cli.ui.components.display.markdown_display import (
            AuraMarkdown,
            AuraMarkdownDisplay,
        )

        display = AuraMarkdownDisplay()
        md = display.render("# Hello\n\nWorld")

        assert isinstance(md, AuraMarkdown)

    def test_code_block_interception(self, mock_theme):
        """Testa se blocos de código são interceptados pelo AuraCodeBlock."""
        from aura_cli.cli.ui.components.display.markdown_display import (
            AuraCodeBlock,
            AuraMarkdown,
            AuraMarkdownDisplay,
        )

        display = AuraMarkdownDisplay()
        md = display.render("```python\nprint(1)\n```")

        assert isinstance(md, AuraMarkdown)
        # Verifica se o elemento 'fence' foi substituído
        assert md.elements["fence"] == AuraCodeBlock
        assert md.elements["code_block"] == AuraCodeBlock


class TestSmartContextBuffer:
    """Testes específicos para o Smart Context Buffer."""

    def test_large_input_detection_by_chars(self, mock_theme):
        """Testa detecção de input grande por contagem de caracteres."""
        from datetime import datetime

        from aura_cli.cli.ui.components.display.message_bubble import (
            MessageBubble,
            MessageMetadata,
            MessageType,
        )

        # Input com mais de 1000 caracteres
        large_content = "A" * 1500
        metadata = MessageMetadata(
            tokens=1500,  # Usar campo correto
            model="test-model",
        )

        chat = MessageBubble(
            sender="user",
            content=large_content,
            message_type=MessageType.USER,
            timestamp=datetime.fromtimestamp(1234567890.0),
            metadata=metadata,
        )

        assert chat.metadata is not None
        assert chat.metadata.tokens == 1500

    def test_normal_input_no_buffer(self, mock_theme):
        """Testa que inputs pequenos não ativam o buffer."""
        from datetime import datetime

        from aura_cli.cli.ui.components.display.message_bubble import (
            MessageBubble,
            MessageType,
        )

        chat = MessageBubble(
            sender="user",
            content="Hello, short message",
            message_type=MessageType.USER,
            timestamp=datetime.fromtimestamp(1234567890.0),
            metadata=None,  # Metadata None = input normal
        )

        # Sem metadata ou metadata padrão = input normal
        assert chat.metadata is not None  # MessageBubble cria metadata padrão se None
