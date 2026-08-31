from types import SimpleNamespace
from unittest.mock import Mock

from aura_cli.core.agents.conversation_instrumentation import (
    instrument_agent_conversation,
)


def test_instrumentation_observes_send_and_receive_without_changing_results() -> None:
    proxy = SimpleNamespace(name="proxy", send=Mock(return_value="sent"))
    assistant = SimpleNamespace(name="assistant", receive=Mock(return_value="received"))
    original_send = proxy.send
    original_receive = assistant.receive
    observer = Mock()

    instrument_agent_conversation(
        user_proxy=proxy,
        assistant=assistant,
        observer=observer,
    )

    recipient = SimpleNamespace(name="recipient")
    sender = SimpleNamespace(name="sender")
    assert proxy.send({"content": "out"}, recipient, True, False) == "sent"
    assert assistant.receive({"content": "in"}, sender, False, True) == "received"
    assert observer.call_args_list[0].args == (
        {"content": "out"},
        "proxy",
        "recipient",
        "send",
    )
    assert observer.call_args_list[1].args == (
        {"content": "in"},
        "sender",
        "assistant",
        "receive",
    )
    original_send.assert_called_once_with({"content": "out"}, recipient, True, False)
    original_receive.assert_called_once_with({"content": "in"}, sender, False, True)


def test_instrumentation_accepts_backends_without_optional_methods() -> None:
    instrument_agent_conversation(
        user_proxy=object(),
        assistant=object(),
        observer=Mock(),
    )
