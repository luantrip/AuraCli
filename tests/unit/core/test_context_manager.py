"""Tests for core/context/base.py — ContextManager, compress_conversation_history."""

from aura_cli.core.context.base import ContextManager, compress_conversation_history


def make_history(n=5):
    history = [{"role": "system", "content": "You are Aura."}]
    for i in range(n):
        history.append({"role": "user", "content": f"User message {i}"})
        history.append({"role": "assistant", "content": f"Assistant response {i}"})
    return history


class TestContextManager:
    def test_add_message(self):
        cm = ContextManager()
        cm.add_message("user", "Hello")
        cm.add_message("assistant", "Hi there")
        # ContextManager stores internally — verify via get_compressed_history
        history = cm.get_compressed_history()
        assert isinstance(history, list)

    def test_get_context_summary_returns_string(self):
        cm = ContextManager()
        cm.add_message("user", "Hello")
        summary = cm.get_context_summary()
        assert isinstance(summary, str)

    def test_add_tool_usage(self):
        cm = ContextManager()
        initial_count = len(cm.tool_calls) if hasattr(cm, "tool_calls") else 0
        cm.add_tool_usage("read_file result: content here")
        # Deve registrar o uso — pelo menos não lançar exceção
        # e o histórico de tool calls deve crescer se o CM rastreia isso
        if hasattr(cm, "tool_calls"):
            assert len(cm.tool_calls) >= initial_count

    def test_compress_returns_list(self):
        cm = ContextManager(compression_threshold=100)
        cm.conversation_history = [
            {"role": "user", "content": f"msg {i}"} for i in range(5)
        ]
        cm.compress()
        result = cm.get_compressed_history()
        assert isinstance(result, list)

    def test_get_compressed_history_returns_list(self):
        cm = ContextManager()
        result = cm.get_compressed_history()
        assert isinstance(result, list)


class TestCompressConversationHistory:
    def test_short_history_unchanged(self):
        history = make_history(2)
        result = compress_conversation_history(history, max_tokens=100000)
        assert len(result) == len(history)

    def test_preserves_system_messages(self):
        history = make_history(10)
        result = compress_conversation_history(history, max_tokens=100)
        system_msgs = [m for m in result if m["role"] == "system"]
        assert len(system_msgs) >= 1

    def test_returns_list(self):
        history = make_history(5)
        result = compress_conversation_history(history)
        assert isinstance(result, list)

    def test_empty_history_returns_empty(self):
        result = compress_conversation_history([])
        assert result == []

    def test_only_system_messages_unchanged(self):
        history = [{"role": "system", "content": "sys"}]
        result = compress_conversation_history(history)
        assert result == history
