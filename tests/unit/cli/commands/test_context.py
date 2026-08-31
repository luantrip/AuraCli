"""Tests for context commands module.

Tests for /tangent and /checkpoint command handlers.
"""

from unittest.mock import MagicMock


class TestHandleTangent:
    """Tests for handle_tangent function."""

    def test_tangent_toggle_not_active(self):
        """Test toggling tangent when not active."""
        from aura_cli.cli.commands.context import handle_tangent
        from aura_cli.core.tangent.manager import TangentManager

        conversation = [{"role": "user", "content": "test"}]
        tangent_manager = TangentManager()

        result_messages, result_text = handle_tangent("", conversation, tangent_manager)

        assert result_messages == []
        assert tangent_manager.in_tangent is True
        assert "tangent" in result_text.lower() or "context" in result_text.lower()

    def test_tangent_toggle_active(self):
        """Test toggling tangent when active."""
        from aura_cli.cli.commands.context import handle_tangent
        from aura_cli.core.tangent.manager import TangentManager

        checkpoint_messages = [{"role": "user", "content": "base"}]
        tangent_messages = [
            *checkpoint_messages,
            {"role": "user", "content": "tangent"},
            {"role": "assistant", "content": "reply"},
        ]
        tangent_manager = TangentManager()
        tangent_manager.enter(checkpoint_messages)

        result_messages, result_text = handle_tangent(
            "", tangent_messages, tangent_manager
        )

        assert result_messages == checkpoint_messages
        assert tangent_manager.in_tangent is False
        assert "restored" in result_text.lower() or "checkpoint" in result_text.lower()

    def test_tangent_tail_not_active(self):
        """Test tangent tail when not active."""
        from aura_cli.cli.commands.context import handle_tangent
        from aura_cli.core.tangent.manager import TangentManager

        conversation = []
        tangent_manager = TangentManager()

        result_messages, result_text = handle_tangent(
            "tail", conversation, tangent_manager
        )

        assert result_messages == conversation
        assert "não" in result_text.lower() or "not" in result_text.lower()

    def test_tangent_tail_active(self):
        """Test tangent tail when active."""
        from aura_cli.cli.commands.context import handle_tangent
        from aura_cli.core.tangent.manager import TangentManager

        checkpoint_messages = [{"role": "user", "content": "base"}]
        tangent_messages = [
            *checkpoint_messages,
            {"role": "user", "content": "tangent"},
            {"role": "assistant", "content": "reply"},
        ]
        tangent_manager = TangentManager()
        tangent_manager.enter(checkpoint_messages)

        result_messages, result_text = handle_tangent(
            "tail", tangent_messages, tangent_manager
        )

        assert result_messages == tangent_messages
        assert tangent_manager.in_tangent is False
        assert "preserved" in result_text.lower() or "checkpoint" in result_text.lower()

    def test_tangent_unknown_command(self):
        """Test tangent with unknown subcommand."""
        from aura_cli.cli.commands.context import handle_tangent
        from aura_cli.core.tangent.manager import TangentManager

        conversation = []
        tangent_manager = TangentManager()

        result_messages, result_text = handle_tangent(
            "unknown", conversation, tangent_manager
        )

        assert result_messages == conversation
        assert "unknown" in result_text.lower()


class TestHandleCheckpoint:
    """Tests for handle_checkpoint function."""

    def test_checkpoint_init(self):
        """Test checkpoint init command."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()

        success, _state, message = handle_checkpoint("init", checkpoint_manager)

        assert success is True
        checkpoint_manager.init.assert_called_once()
        assert "inicializado" in message.lower() or "initialized" in message.lower()

    def test_checkpoint_create_with_description(self):
        """Test checkpoint create with description."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()

        success, _state, message = handle_checkpoint(
            "create My checkpoint", checkpoint_manager
        )

        assert success is True
        checkpoint_manager.create.assert_called_once_with(
            "My checkpoint", conversation_state=None
        )
        assert "checkpoint" in message.lower() and (
            "criado" in message.lower() or "created" in message.lower()
        )

    def test_checkpoint_create_without_description(self):
        """Test checkpoint create without description."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()

        success, _state, message = handle_checkpoint("create", checkpoint_manager)

        assert success is True
        assert "obrigatória" in message.lower() or "required" in message.lower()

    def test_checkpoint_restore(self):
        """Test checkpoint restore command without id (usage error)."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()

        success, _state, message = handle_checkpoint("restore", checkpoint_manager)

        assert success is True
        # Restore without id shows usage
        assert (
            "uso" in message.lower()
            or "id" in message.lower()
            or "obrigatório" in message.lower()
        )

    def test_checkpoint_restore_with_id(self):
        """Test checkpoint restore with valid id."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()
        checkpoint_manager.restore.return_value = (
            True,
            {"messages": [{"role": "user", "content": "hi"}]},
        )

        success, state, message = handle_checkpoint(
            "restore abc123", checkpoint_manager
        )

        assert success is True
        assert state == {"messages": [{"role": "user", "content": "hi"}]}
        checkpoint_manager.restore.assert_called_once_with("abc123", hard=False)
        assert "restaurado" in message.lower() or "restored" in message.lower()

    def test_checkpoint_list_empty(self):
        """Test checkpoint list when no checkpoints."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()
        checkpoint_manager.list.return_value = []

        success, _state, message = handle_checkpoint("list", checkpoint_manager)

        assert success is True
        assert "nenhum" in message.lower() or "none" in message.lower()

    def test_checkpoint_list_with_limit(self):
        """Test checkpoint list with numeric limit."""
        from datetime import datetime

        from aura_cli.cli.commands.context import handle_checkpoint
        from aura_cli.core.checkpoint.manager import Checkpoint

        checkpoint_manager = MagicMock()
        checkpoint_manager.list.return_value = [
            Checkpoint("a1", "First", datetime.now(), []),
            Checkpoint("b2", "Second", datetime.now(), []),
        ]

        success, _state, _message = handle_checkpoint("list 5", checkpoint_manager)

        assert success is True
        checkpoint_manager.list.assert_called_once_with(limit=5)

    def test_checkpoint_restore_invalid_id(self):
        """Test checkpoint restore with invalid id (restore returns False)."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()
        checkpoint_manager.restore.return_value = (False, None)

        success, state, message = handle_checkpoint(
            "restore invalid_id", checkpoint_manager
        )

        assert success is True
        assert state is None
        assert (
            "falha" in message.lower()
            or "fail" in message.lower()
            or "verifique" in message.lower()
        )

    def test_checkpoint_restore_hard(self):
        """Test checkpoint restore with hard flag."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()
        checkpoint_manager.restore.return_value = (True, {"messages": []})

        success, _state, message = handle_checkpoint(
            "restore hard abc123", checkpoint_manager
        )

        assert success is True
        checkpoint_manager.restore.assert_called_once_with("abc123", hard=True)
        assert "restaurado" in message.lower() or "restored" in message.lower()
        assert "hard" in message.lower()

    def test_checkpoint_unknown_command(self):
        """Test checkpoint with unknown subcommand."""
        from aura_cli.cli.commands.context import handle_checkpoint

        checkpoint_manager = MagicMock()

        success, _state, message = handle_checkpoint("unknown", checkpoint_manager)

        assert success is True
        assert "unknown" in message.lower()
