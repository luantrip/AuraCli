from aura_cli.core.agents.agent_communication import CommunicationManager, MessageType


def test_send_response_routes_to_original_sender_only():
    manager = CommunicationManager()
    manager.create_channel("main", "Main")
    manager.register_agent("agent_a", "main")
    manager.register_agent("agent_b", "main")
    manager.register_agent("agent_c", "main")

    message_id = manager.send_message(
        "agent_a",
        "agent_b",
        MessageType.REQUEST,
        {"action": "analyze"},
        channel_id="main",
        requires_response=True,
    )

    request = manager.receive_message("agent_b", channel_id="main", timeout=0.1)
    assert request is not None
    assert request.id == message_id

    response_id = manager.get_channel("main").send_response(  # type: ignore[union-attr]
        "agent_b",
        message_id,
        {"status": "done"},
    )

    response = manager.receive_message("agent_a", channel_id="main", timeout=0.1)
    assert response is not None
    assert response.id == response_id
    assert response.response_to == message_id
    assert response.content == {"status": "done"}

    assert manager.receive_message("agent_c", channel_id="main", timeout=0.1) is None


def test_wait_for_response_returns_linked_response():
    manager = CommunicationManager()
    manager.create_channel("main", "Main")
    manager.register_agent("agent_a", "main")
    manager.register_agent("agent_b", "main")

    message_id = manager.send_message(
        "agent_a",
        "agent_b",
        MessageType.REQUEST,
        "ping",
        channel_id="main",
        requires_response=True,
    )

    request = manager.receive_message("agent_b", channel_id="main", timeout=0.1)
    assert request is not None

    manager.get_channel("main").send_response(  # type: ignore[union-attr]
        "agent_b",
        message_id,
        "pong",
    )

    response = manager.wait_for_response(message_id, channel_id="main", timeout=0.1)
    assert response is not None
    assert response.content == "pong"
    assert response.response_to == message_id
