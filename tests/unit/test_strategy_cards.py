from aura_cli.core.agents.strategy_deck import StrategyDeck
from aura_cli.core.agents.strategy_injector import (
    inject_card_into_prompt,
    strip_card_from_prompt,
)


def test_strategy_deck_is_seeded_and_unique():
    deck = StrategyDeck()
    first = deck.draw(20, seed=7)
    second = deck.draw(20, seed=7)
    assert first == second
    assert len({(card.reasoning_id, card.workflow_id, card.strategy_id) for card in first}) == 20


def test_strategy_card_round_trip():
    prompt = "solve it"
    enriched = inject_card_into_prompt(prompt, StrategyDeck().draw_one(seed=1))
    assert "YOUR STRATEGY CARD" in enriched
    assert strip_card_from_prompt(enriched) == prompt
