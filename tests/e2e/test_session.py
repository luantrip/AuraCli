"""Testes End-to-End de sessão."""


class TestE2ESession:
    """Testes E2E de sessão completa."""

    def test_ui_manager_lifecycle(self):
        """Testa ciclo de vida completo do UIManager."""
        from aura_cli.cli.ui.manager import UIManager

        # Inicialização
        ui = UIManager()
        assert ui is not None

        # Uso
        ui.show_idle()
        ui.show_thinking()
        ui.stop_status()

        # Finalização
        assert ui.stats.current_status == "idle"

    def test_stats_tracking_lifecycle(self):
        """Testa ciclo de vida de rastreamento de stats."""
        from aura_cli.core.stats import get_stats

        stats = get_stats()

        # Rastreia operações
        stats.increment_files_edited()
        stats.add_tokens(
            {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        )

        assert stats.files_edited > 0
        assert stats.tokens_used > 0

    def test_context_compression_lifecycle(self):
        """Testa ciclo de vida de compactação de contexto."""
        from aura_cli.core.context.base import compress_conversation_history

        messages = [
            {"role": "user", "content": "msg" * 100},
            {"role": "assistant", "content": "resp" * 100},
            {"role": "user", "content": "msg2"},
        ]

        compressed = compress_conversation_history(messages, max_tokens=500)

        assert isinstance(compressed, list)
        assert len(compressed) <= len(messages)
