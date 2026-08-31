"""Testes de integração para fluxo de chat."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from aura_cli.cli.function_call_handler import process_function_calls_loop
from tests.runtime_helpers import make_runtime_services


class TestChatFlowIntegration:
    """Testes de integração do fluxo de chat."""

    def test_ui_manager_exists(self):
        """Testa que UIManager existe."""
        from aura_cli.cli.ui.manager import UIManager

        assert UIManager is not None

    def test_stats_integration(self):
        """Testa integração com Stats."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()
        assert stats is not None

    def test_context_manager_exists(self):
        """Testa que ContextManager existe."""
        from aura_cli.core.context.base import ContextManager

        assert ContextManager is not None

    @pytest.mark.asyncio
    @patch("aura_cli.cli.helpers.get_api_keys_dict")
    @patch("aura_cli.cli.utils.worker_factory.create_agi_worker_thread")
    async def test_chat_flow_recovers_from_tool_failure_and_delegates_to_agi(
        self,
        mock_create_agi_worker,
        mock_api_keys,
    ):
        """The general chat should recover from a failed tool call and still delegate."""
        from aura_cli.cli.app_loop import AppLoop

        mock_api_keys.return_value = {"NVIDIA_API_KEY": "nv-key"}

        agi_worker = MagicMock(task_id="agi_task_integration")
        agi_thread = MagicMock()
        agi_thread.name = "agi_thread_integration"
        mock_create_agi_worker.return_value = (agi_worker, agi_thread)

        ui = Mock()
        ui.status_queue = Mock()
        stats = Mock()
        stats._files_read_list = []
        stats.increment_tool_calls = Mock()
        console = Mock()

        app_loop = AppLoop(
            ui=ui,
            stats=stats,
            console=console,
            conversation_history=[
                {"role": "system", "content": "You are Aura."},
                {"role": "user", "content": "Refatore auth e depois acione a AGI."},
            ],
            context_manager=Mock(),
            available_tools={},
            initial_model="openai/nvidia/llama-3.3-nemotron-super-49b-v1",
            project_root=Path("/tmp"),
            runtime_services=make_runtime_services(Path("/tmp")),
        )

        first_response = Mock()
        first_message = Mock()
        first_message.function_call = None
        first_message.tool_calls = [
            {
                "id": "call_broken",
                "type": "function",
                "function": {"name": "broken_tool", "arguments": "{}"},
            }
        ]
        first_response.choices = [Mock(message=first_message)]

        second_response = Mock()
        second_message = Mock()
        second_message.function_call = None
        second_message.tool_calls = [
            {
                "id": "call_delegate",
                "type": "function",
                "function": {
                    "name": "delegate_to_agi",
                    "arguments": '{"objective":"Refatorar o módulo de autenticação"}',
                },
            }
        ]
        second_response.choices = [Mock(message=second_message)]

        third_response = Mock()
        third_message = Mock()
        third_message.function_call = None
        third_message.tool_calls = None
        third_message.content = "Deleguei para a AGI após recuperar da falha."
        third_response.choices = [Mock(message=third_message)]

        with patch(
            "aura_cli.cli.function_call_handler.query_with_fallback",
            side_effect=[first_response, second_response, third_response],
        ):
            response_text, _ = await process_function_calls_loop(
                model="openai/nvidia/llama-3.3-nemotron-super-49b-v1",
                conversation_history=app_loop.conversation_history,
                tool_schemas=[],
                available_tools={
                    "broken_tool": Mock(side_effect=Exception("boom")),
                    "delegate_to_agi": app_loop._do_delegate_to_agi,
                },
                stats=stats,
                ui=ui,
                console=console,
                max_calls=5,
                suppress_tool_loading=True,
            )

        assert response_text == "Deleguei para a AGI após recuperar da falha."
        assert app_loop.agi_thread is agi_thread
        tool_messages = [
            msg for msg in app_loop.conversation_history if msg.get("role") == "tool"
        ]
        assert any("broken_tool" in msg["content"] for msg in tool_messages)
        assert any("agi_task_integration" in msg["content"] for msg in tool_messages)
