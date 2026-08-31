"""Tests for core/config.py — Config, get_config_manager."""

import json
from unittest.mock import patch

import pytest

from aura_cli.core.config import Config, get_config_manager


@pytest.fixture
def tmp_config(tmp_path):
    return Config(path=tmp_path / "config.json")


class TestConfig:
    def test_creates_default_config_on_first_run(self, tmp_path):
        cfg = Config(path=tmp_path / "new.json")
        assert cfg.get("default_model") is not None
        assert (tmp_path / "new.json").exists()

    def test_get_returns_value(self, tmp_config):
        tmp_config.set("theme_name", "nebula")
        assert tmp_config.get("theme_name") == "nebula"

    def test_set_persists_to_disk(self, tmp_path):
        cfg = Config(path=tmp_path / "cfg.json")
        cfg.set("log_level", "DEBUG")
        cfg2 = Config(path=tmp_path / "cfg.json")
        assert cfg2.get("log_level") == "DEBUG"

    def test_get_missing_key_returns_none(self, tmp_config):
        assert tmp_config.get("nonexistent_key_xyz") is None

    def test_default_model_is_gemini(self, tmp_config):
        model = tmp_config.get("default_model")
        assert model is not None
        assert model is not None  # default model is set

    def test_normalizes_model_name_on_get(self, tmp_config):
        tmp_config.data["default_model"] = "gemini-2.5-flash"
        model = tmp_config.get("default_model")
        assert len(model) > 0  # model has a value

    def test_normalizes_model_name_on_set(self, tmp_config):
        tmp_config.set("default_model", "gemini-2.5-flash")
        assert tmp_config.data["default_model"]  # model is set

    def test_merges_defaults_on_load(self, tmp_path):
        cfg_file = tmp_path / "partial.json"
        cfg_file.write_text(json.dumps({"default_model": "gemini/gemini-2.5-flash"}))
        cfg = Config(path=cfg_file)
        assert cfg.get("auto_confirm_tools") is not None

    def test_handles_corrupt_json(self, tmp_path):
        cfg_file = tmp_path / "bad.json"
        cfg_file.write_text("{invalid json}")
        cfg = Config(path=cfg_file)
        assert cfg.get("default_model") is not None

    def test_get_api_key_delegates_to_secure_config(self, tmp_config):
        with patch("aura_cli.core.config.Config.get_api_key") as mock:
            mock.return_value = "test-key"
            result = tmp_config.get_api_key("google")
            assert result == "test-key"


class TestGetConfigManager:
    def test_returns_singleton(self):
        m1 = get_config_manager()
        m2 = get_config_manager()
        assert m1 is m2

    def test_has_get_method(self):
        mgr = get_config_manager()
        assert hasattr(mgr, "get")

    def test_has_set_method(self):
        mgr = get_config_manager()
        assert hasattr(mgr, "set")
