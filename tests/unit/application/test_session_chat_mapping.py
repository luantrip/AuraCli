from datetime import datetime

from aura_cli.application.sessions import chat_messages_to_history, role_to_sender


def test_chat_mapping_filters_empty_messages_and_preserves_metadata() -> None:
    history = chat_messages_to_history(
        [
            {"sender": "User", "content": "hello", "task_id": "task"},
            {"sender": "Aura", "content": ""},
        ],
        clock=lambda: datetime(2026, 1, 2, 3, 4, 5),
    )

    assert history == [
        {
            "role": "user",
            "content": "hello",
            "timestamp": "2026-01-02T03:04:05",
            "metadata": {"sender": "User", "task_id": "task"},
        }
    ]


def test_unknown_sender_and_role_have_assistant_defaults() -> None:
    history = chat_messages_to_history([{"sender": "Custom", "content": "hello"}])

    assert history[0]["role"] == "assistant"
    assert role_to_sender("custom") == "Aura"
