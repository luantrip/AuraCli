"""Tests for opt-in accessibility configuration semantics."""

import json

from aura_cli.cli.ui import display_facade
from aura_cli.core.config import AppSettings, ConfigCompat, JsonConfigRepository


def test_accessibility_is_disabled_by_default() -> None:
    settings = AppSettings()

    assert settings.accessibility.enabled is False
    assert settings.accessibility.device == "auto"
    assert settings.accessibility.screen_reader is None


def test_legacy_display_accessible_setting_is_migrated(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"display": {"accessible": True}}), encoding="utf-8")

    settings = JsonConfigRepository(path).load()

    assert settings.accessibility.enabled is True
    assert settings.accessibility.device == "auto"


def test_compatibility_wrapper_exposes_and_persists_accessibility(tmp_path) -> None:
    repository = JsonConfigRepository(tmp_path / "config.json")
    config = ConfigCompat(repository)

    config.set("accessibility_device", "screen_reader")
    config.set("accessibility_screen_reader", "voiceover")
    config.set("accessibility_mode", True)

    assert config.get("accessibility_mode") is True
    assert config.get("accessibility_device") == "screen_reader"
    assert config.get("accessibility_screen_reader") == "voiceover"


def test_screen_reader_metadata_does_not_enable_mode(monkeypatch, tmp_path) -> None:
    monkeypatch.delenv("AURA_ACCESSIBLE", raising=False)
    config = ConfigCompat(JsonConfigRepository(tmp_path / "config.json"))
    config.set("accessibility_mode", False)
    config.set("accessibility_screen_reader", "voiceover")

    monkeypatch.setattr(
        "aura_cli.core.config.get_config_manager", lambda: config
    )
    assert display_facade._is_accessible_mode() is False
