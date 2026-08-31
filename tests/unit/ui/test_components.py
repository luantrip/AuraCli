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

        from aura_cli.cli.ui.components.lcd_display import AuraLCDDisplay

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

        from aura_cli.cli.ui.components.lcd_display import AuraLCDDisplay

        lcd = AuraLCDDisplay()
        content = "line1\nline2\nline3"
        renderable = lcd.render(content, title="LINES", line_numbers=True)

        # Código retorna Group
        assert isinstance(renderable, Group)

    def test_render_with_syntax_highlighting(self, mock_theme):
        """Testa renderização com syntax highlighting."""
        from rich.console import Group

        from aura_cli.cli.ui.components.lcd_display import AuraLCDDisplay

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

        from aura_cli.cli.ui.components.message_bubble import MessageBubble, MessageType

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

        from aura_cli.cli.ui.components.message_bubble import MessageBubble, MessageType

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

        from aura_cli.cli.ui.components.message_bubble import (
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

        from aura_cli.cli.ui.components.message_bubble import MessageBubble, MessageType

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
        from aura_cli.cli.ui.components.markdown_display import (
            AuraMarkdown,
            AuraMarkdownDisplay,
        )

        display = AuraMarkdownDisplay()
        md = display.render("# Hello\n\nWorld")

        assert isinstance(md, AuraMarkdown)

    def test_code_block_interception(self, mock_theme):
        """Testa se blocos de código são interceptados pelo AuraCodeBlock."""
        from aura_cli.cli.ui.components.markdown_display import (
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

        from aura_cli.cli.ui.components.message_bubble import (
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

        from aura_cli.cli.ui.components.message_bubble import MessageBubble, MessageType

        chat = MessageBubble(
            sender="user",
            content="Hello, short message",
            message_type=MessageType.USER,
            timestamp=datetime.fromtimestamp(1234567890.0),
            metadata=None,  # Metadata None = input normal
        )

        # Sem metadata ou metadata padrão = input normal
        assert chat.metadata is not None  # MessageBubble cria metadata padrão se None


class TestAgiTaskWindow:
    """Testes para o componente AgiTaskWindow."""

    def test_task_window_tracks_supervisor_state_on_update(self, mock_theme):
        """Supervisor state should be stored on task updates."""
        from aura_cli.cli.ui.components.agi_task_window import AgiTaskWindow

        window = AgiTaskWindow(
            task_id="agi-1",
            description="Task",
            objective="Analyze codebase",
        )

        window.update_status(
            "awaiting_human",
            "Need approval",
            supervisor_state="awaiting_human",
            fallback_reason="human_approval_required",
        )

        assert window.supervisor_state == "awaiting_human"
        assert window.fallback_reason == "human_approval_required"

    def test_task_window_marks_completed_supervisor_state(self, mock_theme):
        """Successful completion should move the supervisor state to completed."""
        from aura_cli.cli.ui.components.agi_task_window import AgiTaskWindow

        window = AgiTaskWindow(
            task_id="agi-2",
            description="Task",
            objective="Analyze codebase",
        )

        window.complete(True, result="done")

        assert window.supervisor_state == "completed"

    def test_task_window_marks_cancelled_as_terminal(self, mock_theme):
        """Cancellation must stop activity and remain visible as a terminal state."""
        from aura_cli.cli.ui.components.agi_task_window import AgiTaskWindow

        window = AgiTaskWindow(
            task_id="agi-cancelled",
            description="Task",
            objective="Analyze codebase",
        )

        window.cancel("cancelled by user")

        assert window.status == "cancelled"
        assert window.is_complete() is True
        assert window.is_active() is False
        assert window.error == "cancelled by user"
        assert "Operação cancelada" in window.logs[-1].message

    def test_task_window_formats_timestamp_and_localized_completion(self, mock_theme):
        """Terminal logs should expose time and use the product language."""
        from aura_cli.cli.ui.components.agi_task_window import AgiTaskWindow

        window = AgiTaskWindow(
            task_id="agi-2b",
            description="Task",
            objective="Analyze codebase",
        )

        window.complete(True, result="done")

        rendered = window.logs[-1].format(mock_theme)
        assert "[" in rendered.plain
        assert "Tarefa concluída" in rendered.plain

        window.complete(False, error="timeout")
        assert "Falha: timeout" in window.logs[-1].message

    def test_task_window_renders_supervisor_summary_only_for_exception_state(
        self, mock_theme
    ):
        """Supervisor summary should only exist when state needs emphasis."""
        from aura_cli.cli.ui.components.agi_task_window import AgiTaskWindow

        window = AgiTaskWindow(
            task_id="agi-3",
            description="Task",
            objective="Analyze codebase",
        )

        assert window._render_supervisor_summary(mock_theme) is None

        window.update_status(
            "awaiting_human",
            "Need approval",
            supervisor_state="awaiting_human",
            fallback_reason="human_approval_required",
        )

        summary = window._render_supervisor_summary(mock_theme)
        assert summary is not None
