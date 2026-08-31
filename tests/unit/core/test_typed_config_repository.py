"""Contracts for the canonical typed configuration repository."""

from aura_cli.core.config import AppSettings, ConfigCompat, JsonConfigRepository


def test_json_repository_roundtrip_is_typed_and_atomic(tmp_path) -> None:
    path = tmp_path / "config.json"
    repository = JsonConfigRepository(path)
    settings = AppSettings(default_model="openai/gpt-4o", theme_name="dark")

    repository.save(settings)

    loaded = repository.load()
    assert isinstance(loaded, AppSettings)
    assert loaded.default_model == "openai/gpt-4o"
    assert loaded.theme_name == "dark"
    assert not path.with_suffix(".json.tmp").exists()


def test_compatibility_api_uses_injected_repository(tmp_path) -> None:
    repository = JsonConfigRepository(tmp_path / "config.json")
    config = ConfigCompat(repository=repository)

    config.set("theme_name", "nebula")

    assert repository.load().theme_name == "nebula"
