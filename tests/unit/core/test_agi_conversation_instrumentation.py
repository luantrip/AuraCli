from unittest.mock import Mock, patch

from aura_cli.core.agi.execution import AgiExecutionEngine


def _engine() -> AgiExecutionEngine:
    engine = object.__new__(AgiExecutionEngine)
    engine.task_id = "agi-1"
    engine.event_adapter = Mock()
    engine.validator = Mock()
    engine.communication_manager = Mock()
    engine.agent_memory = Mock()
    engine._extract_file_artifacts = Mock()
    return engine


@patch("aura_cli.core.agi.execution.time.time", return_value=21.5)
def test_agi_observer_publishes_and_persists_received_discovery(_clock) -> None:
    engine = _engine()
    message = {"content": "Identifiquei uma decisão arquitetural " + "x" * 30}

    engine._observe_agent_message(message, "specialist", "aura_agi", "receive")

    engine.event_adapter.emit_chat_message.assert_called_once_with(
        sender="specialist", content=message["content"], task_id="agi-1"
    )
    engine.agent_memory.store.assert_called_once_with(
        agent_id="aura_agi",
        key="discovery_21",
        value=message["content"],
        context={"sender": "specialist", "timestamp": 21.5},
        ttl=3600,
    )
    engine.validator.extract_learned_rules_from_response.assert_called_once_with(
        message["content"]
    )


def test_agi_observer_does_not_persist_outgoing_message() -> None:
    engine = _engine()
    message = {"content": "Identifiquei uma decisão arquitetural " + "x" * 30}

    engine._observe_agent_message(message, "proxy", "aura_agi", "send")

    engine.agent_memory.store.assert_not_called()
    engine.validator.extract_learned_rules_from_response.assert_not_called()
