"""Tests for canonical conversation history operations."""

from aura_cli.application.conversation import (
    append_tool_interaction,
    build_tool_result_response,
)


def test_append_tool_interaction_writes_provider_pair() -> None:
    history = []
    append_tool_interaction(
        history,
        name="read_file",
        arguments={"path": "a.py"},
        call_id="call-1",
        content="source",
    )

    assert [message["role"] for message in history] == ["assistant", "tool"]
    assert history[0]["tool_calls"][0]["function"]["arguments"] == '{"path": "a.py"}'
    assert history[1]["tool_call_id"] == "call-1"


def test_build_tool_result_response_uses_recent_results() -> None:
    history = [{"role": "tool", "name": "write_file", "content": "escrito com sucesso"}]

    response = build_tool_result_response(history, "crie o arquivo")

    assert "Concluí: crie o arquivo" in response
    assert "Arquivo modificado com sucesso" in response
