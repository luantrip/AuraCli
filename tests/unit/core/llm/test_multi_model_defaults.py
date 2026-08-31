"""Tests for centralized multi-model defaults."""

from unittest.mock import patch

from aura_cli.core.llm.model_utils import get_default_multi_model_candidates


@patch("aura_cli.core.llm.multi_model.HAS_LITELLM", True)
def test_multi_model_default_models_come_from_central_catalog():
    from aura_cli.core.llm.multi_model import MultiModelIntelligence

    intelligence = MultiModelIntelligence()

    assert intelligence.default_models == get_default_multi_model_candidates()
    assert intelligence.models == get_default_multi_model_candidates()


@patch("aura_cli.core.llm.multi_model.HAS_LITELLM", True)
def test_multi_model_preserves_explicit_model_list():
    from aura_cli.core.llm.multi_model import MultiModelIntelligence

    explicit_models = ["gpt-4o-mini", "claude-3-5-haiku-20241022"]
    intelligence = MultiModelIntelligence(models=explicit_models)

    assert intelligence.models == explicit_models


def test_preference_learner_persists_canonical_model_ids(tmp_path):
    from aura_cli.core.llm.multi_model_advanced import ModelPreferenceLearner

    learner = ModelPreferenceLearner(cache_dir=str(tmp_path))
    learner.record_decision(
        task_type="code_edit",
        models_used=["google/gemini-2.5-flash"],
        selected_model="gemini-2.5-flash",
        user_feedback="good",
    )

    assert learner.decision_history[-1]["models_used"] == ["gemini/gemini-2.5-flash"]
    assert learner.get_best_model_for_task("code_edit", ["google/gemini-2.5-flash"])
    assert (
        learner.get_best_model_for_task("code_edit", ["google/gemini-2.5-flash"])
        == "gemini/gemini-2.5-flash"
    )

    restored = ModelPreferenceLearner(cache_dir=str(tmp_path))
    assert (
        restored.get_best_model_for_task("code_edit", ["gemini/gemini-2.5-flash"])
        == "gemini/gemini-2.5-flash"
    )


def test_response_cache_hashes_alias_and_canonical_model_equally(tmp_path):
    from aura_cli.core.llm.multi_model_advanced import ResponseCache

    cache = ResponseCache(cache_dir=str(tmp_path))

    alias_hash = cache.hash_prompt("same prompt", "google/gemini-2.5-flash")
    canonical_hash = cache.hash_prompt("same prompt", "gemini/gemini-2.5-flash")

    assert alias_hash == canonical_hash
