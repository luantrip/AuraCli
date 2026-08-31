"""Tests for centralized ModelProfileManager defaults."""

import json

from aura_cli.core.llm.model_profiles import ModelProfileManager, reset_profile_manager
from aura_cli.core.llm.model_utils import DEFAULT_GEMINI_MODEL, DEFAULT_MODEL


def setup_function():
    reset_profile_manager()
    ModelProfileManager._instance = None


def teardown_function():
    reset_profile_manager()
    ModelProfileManager._instance = None


def test_profile_manager_builds_defaults_from_central_catalog(tmp_path):
    config_path = tmp_path / "model_profiles.json"

    manager = ModelProfileManager(config_path=config_path)

    assert manager.get_model("advanced_reasoning") == DEFAULT_MODEL
    assert manager.get_model("advanced_coding") == DEFAULT_MODEL
    assert manager.get_model("quick_reasoning") == DEFAULT_GEMINI_MODEL
    assert manager.get_model("low_cost_search") == DEFAULT_GEMINI_MODEL
    assert config_path.exists()


def test_profile_manager_preserves_existing_persisted_config(tmp_path):
    config_path = tmp_path / "model_profiles.json"
    existing = {
        "profiles": {
            "advanced_reasoning": "gpt-4o",
            "advanced_coding": "gpt-4o",
            "intermediate_reasoning": "gpt-4o-mini",
            "quick_reasoning": "gpt-4o-mini",
            "intent_router": "gpt-4o-mini",
            "low_cost_search": "gpt-4o-mini",
        },
        "default_profile": "advanced_coding",
        "task_routing": {"patterns": {}},
    }
    config_path.write_text(json.dumps(existing), encoding="utf-8")

    manager = ModelProfileManager(config_path=config_path)

    assert manager.get_model("advanced_reasoning") == "gpt-4o"
    assert manager.get_model("quick_reasoning") == "gpt-4o-mini"


def test_get_model_unknown_profile_falls_back_to_central_default(tmp_path):
    manager = ModelProfileManager(config_path=tmp_path / "model_profiles.json")

    assert manager.get_model("nonexistent-profile") == DEFAULT_MODEL


def test_reset_to_defaults_uses_runtime_default_builder(tmp_path):
    manager = ModelProfileManager(config_path=tmp_path / "model_profiles.json")
    manager.update_profile("quick_reasoning", "gpt-4o-mini")

    manager.reset_to_defaults()

    assert manager.get_model("advanced_coding") == DEFAULT_MODEL
    assert manager.get_model("quick_reasoning") == DEFAULT_GEMINI_MODEL


def test_profile_write_canonicalizes_legacy_alias(tmp_path):
    manager = ModelProfileManager(config_path=tmp_path / "model_profiles.json")

    assert manager.update_profile("quick_reasoning", "google") is True
    assert manager.get_model("quick_reasoning") == DEFAULT_GEMINI_MODEL
    assert manager.list_profiles()["quick_reasoning"] == DEFAULT_GEMINI_MODEL


def test_all_models_are_unique_sorted_canonical_ids(tmp_path):
    manager = ModelProfileManager(config_path=tmp_path / "model_profiles.json")
    manager.update_profile("advanced_reasoning", "gpt-4o")
    manager.update_profile("advanced_coding", "openai")

    models = manager.get_all_models()

    assert models == sorted(set(models))
    assert "gpt-4o" in models
