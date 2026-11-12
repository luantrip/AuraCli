"""F-P1-9 — the history compaction ceiling scales with the model's window.

Pins ``context_hard_limit_for_model`` so a large-window model is not throttled at
a fixed cap, while an explicit user override still wins.
"""

from __future__ import annotations

import pytest

from aura_cli.application.workspace import (
    MIN_CONTEXT_HARD_LIMIT,
    context_hard_limit_for_model,
    context_window_for_model,
)


class TestScalesWithModel:
    @pytest.mark.parametrize(
        "model",
        ["gemini-2.5-flash", "gemini-2.5-pro", "gpt-4o", "claude-sonnet-4-6"],
    )
    def test_large_window_models_get_far_more_than_the_old_fixed_32k(
        self, model: str
    ) -> None:
        limit = context_hard_limit_for_model(model)
        assert limit > 32_000, model  # the regression target
        # Never exceed the model's real window; leave headroom for the response.
        assert limit < context_window_for_model(model), model

    def test_ceiling_is_a_fraction_of_the_window(self) -> None:
        window = context_window_for_model("gpt-4o")
        assert context_hard_limit_for_model("gpt-4o") == int(window * 0.75)

    def test_unknown_model_uses_the_conservative_default_window(self) -> None:
        unknown = context_hard_limit_for_model("totally-made-up-model")
        default_window = context_window_for_model("totally-made-up-model")
        assert unknown == int(default_window * 0.75)
        assert unknown >= MIN_CONTEXT_HARD_LIMIT


class TestExplicitOverride:
    def test_a_positive_override_wins_over_the_per_model_budget(self) -> None:
        # Even for a 1M-window model, a deliberate 50k pin is respected.
        assert context_hard_limit_for_model("gemini-2.5-pro", 50_000) == 50_000

    def test_a_tiny_override_is_clamped_to_the_minimum(self) -> None:
        assert context_hard_limit_for_model("gpt-4o", 10) == MIN_CONTEXT_HARD_LIMIT

    @pytest.mark.parametrize("bad", [0, -1, None])
    def test_non_positive_or_missing_override_falls_back_to_the_model(
        self, bad
    ) -> None:
        assert context_hard_limit_for_model(
            "gpt-4o", bad
        ) == context_hard_limit_for_model("gpt-4o")


class TestNeverBelowFloor:
    def test_result_never_drops_below_the_minimum(self) -> None:
        for model in (None, "", "x", "gpt-4o", "gemini-2.5-pro"):
            assert context_hard_limit_for_model(model) >= MIN_CONTEXT_HARD_LIMIT
