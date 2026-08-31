from unittest.mock import MagicMock

from aura_cli.tui.controllers.conversation import ConversationController
from aura_cli.tui.widgets.message_bubble import MessageType


def test_message_type_normalizes_legacy_sender_names() -> None:
    assert ConversationController.message_type("Sistema") is MessageType.SYSTEM
    assert ConversationController.message_type("System") is MessageType.SYSTEM
    assert ConversationController.message_type("Ferramenta") is MessageType.TOOL
    assert ConversationController.message_type("Erro") is MessageType.ERROR


def test_append_owns_history_and_rendering() -> None:
    host = MagicMock()
    chat = host.query_one.return_value
    bubble = chat.write_bubble.return_value
    controller = ConversationController(host)

    assert controller.append("Aura", "hello", "task-1") is bubble
    assert controller.messages[0]["task_id"] == "task-1"
    assert controller.messages[0]["bubble"] is bubble
