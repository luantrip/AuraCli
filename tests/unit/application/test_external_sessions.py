from aura_cli.application.sessions.external import normalize_external_records


def test_normalizes_grok_acp_messages_and_skips_thoughts() -> None:
    result = normalize_external_records(
        [
            {
                "method": "session/update",
                "params": {
                    "sessionId": "grok-1",
                    "update": {
                        "sessionUpdate": "user_message_chunk",
                        "content": {"type": "text", "text": "Analise o projeto"},
                    },
                },
            },
            {
                "method": "session/update",
                "params": {
                    "update": {
                        "sessionUpdate": "agent_thought_chunk",
                        "content": {"type": "text", "text": "pensamento interno"},
                    }
                },
            },
            {
                "method": "session/update",
                "params": {
                    "update": {
                        "sessionUpdate": "agent_message_chunk",
                        "content": {"type": "text", "text": "Resultado"},
                    }
                },
            },
        ],
        source_format="grok-acp",
    )

    assert result.source_session_id == "grok-1"
    assert [(item["role"], item["content"]) for item in result.messages] == [
        ("user", "Analise o projeto"),
        ("assistant", "Resultado"),
    ]


def test_normalizes_codex_response_items_without_executing_tools() -> None:
    result = normalize_external_records(
        [
            {"type": "session_meta", "thread_id": "codex-1", "cwd": "/tmp/app"},
            {"type": "response_item", "payload": {"type": "message", "role": "user", "content": [{"text": "Corrija"}]}},
            {"type": "response_item", "payload": {"type": "message", "role": "assistant", "content": "Feito"}},
            {"type": "response_item", "payload": {"type": "function_call", "name": "delete_file"}},
        ],
        source_format="codex-rollout",
    )

    assert result.source_session_id == "codex-1"
    assert result.cwd == "/tmp/app"
    assert result.skipped_events == 1
    assert all(item["metadata"]["executable"] is False for item in result.messages)
    assert "nenhum foi executado" in result.warnings[0]


def test_normalizer_deduplicates_adjacent_stream_chunks() -> None:
    result = normalize_external_records(
        [
            {"role": "user", "content": "Olá"},
            {"role": "user", "content": "Olá"},
            {"role": "assistant", "content": "Oi"},
        ],
        source_format="jsonl",
    )

    assert len(result.messages) == 2
