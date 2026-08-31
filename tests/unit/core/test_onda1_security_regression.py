"""Regression tests for Onda 1 credential and workspace-path hardening."""

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from aura_cli.core import secure_config as secure_config_module
from aura_cli.core.config import AppSettings, ConfigCompat
from aura_cli.core.tools import file_system


class MemoryRepository:
    """Small repository double that records typed configuration saves."""

    def __init__(self):
        self.settings = AppSettings()
        self.saved = []

    def load(self):
        return self.settings

    def save(self, settings):
        self.settings = settings
        self.saved.append(deepcopy(settings))


@dataclass
class FakeSecureConfig:
    values: dict
    fail: bool = False

    def set_api_key(self, provider: str, api_key: str) -> None:
        if self.fail:
            raise RuntimeError("keyring unavailable")
        self.values[provider] = api_key

    def delete_api_key(self, provider: str) -> None:
        self.values.pop(provider, None)


def test_config_compat_does_not_persist_secret_in_json(monkeypatch):
    repository = MemoryRepository()
    secure = FakeSecureConfig({})
    monkeypatch.setattr(secure_config_module, "secure_config_manager", secure)

    config = ConfigCompat(repository=repository)
    config.set_api_key("openai", "SENTINEL-MUST-STAY-SECURE")

    assert secure.values["openai"] == "SENTINEL-MUST-STAY-SECURE"
    assert repository.settings.api_keys.openai is None
    assert "SENTINEL-MUST-STAY-SECURE" not in repr(repository.settings.model_dump())


def test_config_compat_generic_api_keys_setter_uses_secure_backend(monkeypatch):
    repository = MemoryRepository()
    secure = FakeSecureConfig({})
    monkeypatch.setattr(secure_config_module, "secure_config_manager", secure)

    config = ConfigCompat(repository=repository)
    config.set("api_keys", {"openai_api_key": "SENTINEL-GENERIC-SET"})

    assert secure.values["openai"] == "SENTINEL-GENERIC-SET"
    assert repository.settings.api_keys.openai is None
    assert "SENTINEL-GENERIC-SET" not in repr(repository.settings.model_dump())


def test_config_compat_does_not_save_when_secure_backend_fails(monkeypatch):
    repository = MemoryRepository()
    secure = FakeSecureConfig({}, fail=True)
    monkeypatch.setattr(secure_config_module, "secure_config_manager", secure)

    config = ConfigCompat(repository=repository)
    with pytest.raises(RuntimeError, match="keyring unavailable"):
        config.set_api_key("openai", "SENTINEL-FAIL-CLOSED")

    assert repository.saved == []
    assert "SENTINEL-FAIL-CLOSED" not in repr(repository.settings.model_dump())


def _enable_workspace_validation(monkeypatch, workspace: Path) -> None:
    monkeypatch.setattr(file_system, "_ALLOWED_BASE_DIR", workspace.resolve())
    monkeypatch.setattr(file_system, "_PATH_VALIDATION_ENABLED", True)


def test_read_code_element_rejects_external_path_before_prism(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside.py"
    workspace.mkdir()
    outside.write_text("def target():\n    pass\n", encoding="utf-8")
    _enable_workspace_validation(monkeypatch, workspace)

    prism_class = MagicMock()
    monkeypatch.setattr("aura_cli.core.memory.prism_bridge.PrismManager", prism_class)

    result = file_system.read_code_element(str(outside), name="target")

    assert "segurança" in result.lower()
    prism_class.assert_not_called()


def test_list_directory_rejects_external_path(monkeypatch, tmp_path):
    workspace = tmp_path / "workspace"
    outside = tmp_path / "outside"
    workspace.mkdir()
    outside.mkdir()
    (outside / "secret.txt").write_text("not for workspace", encoding="utf-8")
    _enable_workspace_validation(monkeypatch, workspace)

    result = file_system.list_directory(str(outside))

    assert "segurança" in result.lower()
    assert "secret.txt" not in result


def test_read_code_element_passes_resolved_workspace_path_to_prism(
    monkeypatch, tmp_path
):
    workspace = tmp_path / "workspace"
    source = workspace / "code.py"
    workspace.mkdir()
    source.write_text("def target():\n    pass\n", encoding="utf-8")
    _enable_workspace_validation(monkeypatch, workspace)

    prism = MagicMock()
    prism.available = True
    chunk = MagicMock(name="target", kind="function", start_line=1, end_line=2)
    chunk.name = "target"
    chunk.kind = "function"
    chunk.start_line = 1
    chunk.end_line = 2
    chunk.content = "def target():\n    pass"
    prism.chunk_file.return_value = [chunk]
    prism_class = MagicMock(return_value=prism)
    monkeypatch.setattr("aura_cli.core.memory.prism_bridge.PrismManager", prism_class)

    result = file_system.read_code_element(str(source), name="target")

    assert "def target" in result
    prism.chunk_file.assert_called_once_with(str(source.resolve()))
