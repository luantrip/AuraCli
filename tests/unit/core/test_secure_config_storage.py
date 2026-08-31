"""Security contracts for API-key persistence."""

import json
import stat
from unittest.mock import Mock, patch

import pytest

from aura_cli.core.config import Config
from aura_cli.core.secure_config import (
    InsecureKeyStorageDisabledError,
    SecureConfig,
)


def test_keyring_is_the_default(tmp_path) -> None:
    config = SecureConfig(path=tmp_path / "config.json")

    assert config._use_keyring is True
    assert config._allow_insecure_file_storage is False


def test_named_profile_uses_isolated_config_and_keyring_namespace(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AURA_HOME", str(tmp_path / "aura-home"))
    config = SecureConfig(profile="work")
    backend = Mock()
    backend.get_password.return_value = "profile-secret"

    with patch("aura_cli.core.secure_config.keyring", backend):
        assert config.get_api_key("openai") == "profile-secret"

    assert config.profile == "work"
    assert config.path == tmp_path / "aura-home" / "profiles" / "work" / "config.json"
    assert config.path.exists()
    backend.get_password.assert_called_once_with("aura_cli:work", "openai_api_key")


def test_lazy_secure_config_reloads_when_profile_changes(monkeypatch) -> None:
    import aura_cli.core.secure_config as module

    module._secure_config_instance = None
    monkeypatch.setenv("AURA_PROFILE", "first")
    first = module.secure_config_manager._instance()
    monkeypatch.setenv("AURA_PROFILE", "second")
    second = module.secure_config_manager._instance()

    assert first is not second
    assert first.profile == "first"
    assert second.profile == "second"


def test_keyring_failure_does_not_write_plaintext(tmp_path) -> None:
    path = tmp_path / "config.json"
    config = SecureConfig(path=path)

    with (
        patch(
            "aura_cli.core.secure_config.keyring.set_password",
            side_effect=RuntimeError("unavailable"),
        ),
        pytest.raises(InsecureKeyStorageDisabledError),
    ):
        config.set_api_key("openai", "secret-value")

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["api_keys"]["openai_api_key"] is None
    assert "secret-value" not in path.read_text(encoding="utf-8")


def test_legacy_config_does_not_fallback_to_plaintext(tmp_path) -> None:
    path = tmp_path / "config.json"
    config = Config(path=path)
    secure_config = Mock()
    secure_config.set_api_key.side_effect = RuntimeError("keyring unavailable")

    with (
        patch("aura_cli.core.secure_config.secure_config_manager", secure_config),
        pytest.raises(RuntimeError, match="keyring unavailable"),
    ):
        config.set_api_key("openai", "legacy-secret")

    assert "legacy-secret" not in path.read_text(encoding="utf-8")


def test_plaintext_storage_requires_explicit_opt_in(tmp_path) -> None:
    path = tmp_path / "config.json"
    config = SecureConfig(path=path, allow_insecure_file_storage=True)

    config.set_api_key("openai", "explicit-secret")

    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["allow_insecure_key_storage"] is True
    assert persisted["api_keys"]["openai_api_key"] == "explicit-secret"
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_first_read_migrates_verified_legacy_key(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("AURA_PROFILE", raising=False)
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"api_keys": {"openai_api_key": "legacy-secret"}}),
        encoding="utf-8",
    )
    config = SecureConfig(path=path)
    keyring_backend = Mock()
    keyring_backend.get_password.side_effect = [None, "legacy-secret"]

    with patch("aura_cli.core.secure_config.keyring", keyring_backend):
        key = config.get_api_key("openai")

    assert key == "legacy-secret"
    keyring_backend.set_password.assert_called_once_with(
        "aura_cli", "openai_api_key", "legacy-secret"
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["api_keys"]["openai_api_key"] is None


def test_migration_clears_plaintext_only_after_keyring_verification(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.delenv("AURA_PROFILE", raising=False)
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"api_keys": {"openai_api_key": "legacy-secret"}}),
        encoding="utf-8",
    )
    config = SecureConfig(path=path)
    keyring_backend = Mock()
    keyring_backend.get_password.return_value = "legacy-secret"

    with patch("aura_cli.core.secure_config.keyring", keyring_backend):
        migrated = config.migrate_keys_to_keyring()

    assert migrated == 1
    keyring_backend.set_password.assert_called_once_with(
        "aura_cli", "openai_api_key", "legacy-secret"
    )
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["api_keys"]["openai_api_key"] is None


def test_failed_migration_preserves_legacy_plaintext(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(
        json.dumps({"api_keys": {"openai_api_key": "legacy-secret"}}),
        encoding="utf-8",
    )
    config = SecureConfig(path=path)
    keyring_backend = Mock()
    keyring_backend.get_password.return_value = None

    with patch("aura_cli.core.secure_config.keyring", keyring_backend):
        migrated = config.migrate_keys_to_keyring()

    assert migrated == 0
    assert config.data["api_keys"]["openai_api_key"] == "legacy-secret"
    persisted = json.loads(path.read_text(encoding="utf-8"))
    assert persisted["api_keys"]["openai_api_key"] == "legacy-secret"
