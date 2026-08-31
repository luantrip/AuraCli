"""Tests for status panel: event extraction and display."""

import queue


class TestStatusPanelEventExtraction:
    """Events with data.content (AGI/Ops chat_message) must be shown."""

    def test_extracts_content_from_event_data(self):
        """create_status_panel should show message when event has data.content."""
        from aura_cli.cli.ui.status_panel import create_status_panel

        q = queue.Queue()
        # Event shape from create_chat_message / QueueAgiAdapter
        q.put(
            {
                "type": "chat_message",
                "task_id": "agi_123",
                "data": {
                    "sender": "agent",
                    "content": "› [Aura AGI] ✓ Contexto carregado.",
                    "metadata": {},
                },
            }
        )
        panel = create_status_panel(q)
        assert panel is not None
        # Panel is a Group of Rich renderables; we only check it was built
        assert q.empty()  # queue was drained

    def test_extracts_plain_string(self):
        """Plain string messages (e.g. Ops status_queue.put(str)) are shown."""
        from aura_cli.cli.ui.status_panel import create_status_panel

        q = queue.Queue()
        q.put("› [Aura Ops] Modo git iniciado...")
        panel = create_status_panel(q)
        assert panel is not None

    def test_empty_queue_returns_none(self):
        from aura_cli.cli.ui.status_panel import create_status_panel

        q = queue.Queue()
        panel = create_status_panel(q)
        assert panel is None

    def test_generic_activity_is_not_dropped(self):
        from aura_cli.cli.ui.status_panel import create_status_panel

        q = queue.Queue()
        q.put("› Cache local atualizado")

        panel = create_status_panel(q)

        assert panel is not None
        assert "Cache local atualizado" in str(panel.renderables)
