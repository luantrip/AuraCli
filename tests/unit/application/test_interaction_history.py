"""Tests for the neutral interaction history model."""

from aura_cli.application.presentation import (
    ConsoleHistory,
    InteractionStatus,
)


def test_history_uses_injected_clock_and_updates_known_fields() -> None:
    history = ConsoleHistory(lambda: 12.5)
    interaction_id = history.add_interaction("prompt")

    assert interaction_id == "interaction_12500"
    assert history.update_interaction(
        interaction_id,
        response="response",
        status=InteractionStatus.SUCCESS,
        prompt_tokens=3,
    )
    interaction = history.get_interaction(interaction_id)
    assert interaction is not None
    assert interaction.timestamp == 12.5
    assert interaction.response == "response"
    assert interaction.prompt_tokens == 3


def test_history_preserves_explicit_id_and_rejects_unknown_update() -> None:
    history = ConsoleHistory(lambda: 1)

    assert history.add_interaction("prompt", "chosen") == "chosen"
    assert history.update_interaction("missing", response="ignored") is False
