"""
Testes para o UIManager e Lógica de Input.
"""

from unittest.mock import MagicMock, patch

import pytest

from aura_cli.cli.ui.manager import UIManager


class TestUIManagerInput:
    @pytest.fixture
    def ui_manager(self):
        # Mock dependencies
        mock_stats = MagicMock()
        mock_queue = MagicMock()
        return UIManager(stats=mock_stats, status_queue=mock_queue)

    @patch("aura_cli.cli.ui.input.Prompt.ask")
    @patch(
        "aura_cli.cli.ui.input.PROMPT_TOOLKIT_AVAILABLE", False
    )  # Force fallback logic
    def test_prompt_normal_input(self, mock_ask, ui_manager):
        """Testa input normal (sem buffer)."""
        mock_ask.return_value = "Short message"

        result = ui_manager.prompt()

        assert result == "Short message"
        # Verifica se evento foi enviado
        ui_manager.status_queue.put.assert_called_once()

        # Verifica conteúdo do evento
        event_dict = ui_manager.status_queue.put.call_args[0][0]
        # ChatMessageEvent.to_dict() returns a dict with 'data' containing sender, content, metadata
        assert event_dict["data"]["content"] == "Short message"
        assert event_dict["data"]["metadata"] == {}  # Metadata vazio

    @patch("aura_cli.cli.ui.input.Prompt.ask")
    @patch("aura_cli.cli.ui.input.PROMPT_TOOLKIT_AVAILABLE", False)
    def test_prompt_smart_buffer_trigger(self, mock_ask, ui_manager):
        """Testa se o Smart Context Buffer ativa para inputs grandes."""
        # Cria um input grande (> 1000 chars)
        large_input = "A" * 1500
        mock_ask.return_value = large_input

        ui_manager.prompt()

        # Verifica evento
        event_dict = ui_manager.status_queue.put.call_args[0][0]
        assert event_dict["data"]["content"] == large_input

        # Metadata deve estar preenchido
        metadata = event_dict["data"]["metadata"]
        assert metadata["is_large_input"] is True
        assert "stats" in metadata
        assert "preview" in metadata
