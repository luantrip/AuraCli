"""Tests for neutral autocomplete and confirmation decisions."""

from aura_cli.application.presentation.autocomplete import FuzzyMatcher
from aura_cli.application.presentation.confirmation import parse_confirmation_answer


def test_fuzzy_match_prioritizes_prefix_and_tolerates_typo() -> None:
    matches = FuzzyMatcher.fuzzy_match("sta", ["status", "settings", "stop"])
    assert matches[0][0] == "status"
    assert FuzzyMatcher.similarity("stats", "status") > 0.5


def test_confirmation_parses_localized_values_defaults_and_invalid_input() -> None:
    assert parse_confirmation_answer(" SIM ", False) is True
    assert parse_confirmation_answer("não", True) is False
    assert parse_confirmation_answer("", True) is True
    assert parse_confirmation_answer("maybe", False) is None
