import json
import logging
from pathlib import Path

import pytest

from aura_cli.core.llm import model_utils


def _load_with(monkeypatch, tmp_path, content: str | None):
    """Run the real loader against a models.json we control."""
    fake_module = tmp_path / "model_utils.py"
    if content is not None:
        (tmp_path / "models.json").write_text(content, encoding="utf-8")
    monkeypatch.setattr(model_utils, "__file__", str(fake_module))
    return model_utils._load_model_presets()


def test_shipped_catalog_loads_and_is_the_effective_source() -> None:
    shipped = json.loads(
        Path(model_utils.__file__).with_name("models.json").read_text(encoding="utf-8")
    )
    assert shipped == model_utils.MODEL_PRESETS


def test_catalog_has_no_duplicate_models_within_a_provider() -> None:
    for provider, models in model_utils.MODEL_PRESETS.items():
        assert len(models) == len(set(models)), provider


def test_catalog_has_no_speculative_gemini_generations() -> None:
    """P1-2: gemini-3.x ids were invented placeholders, not real models."""
    gemini = model_utils.MODEL_PRESETS["gemini"]
    assert all("gemini-2." in m for m in gemini), gemini


def test_every_provider_default_is_in_the_catalog() -> None:
    for provider, default in model_utils._PROVIDER_DEFAULTS.items():
        assert default in model_utils.MODEL_PRESETS[provider], provider


@pytest.mark.parametrize(
    "content",
    [None, "{not json", "[1, 2]", '{"gemini": "not-a-list"}'],
    ids=["missing", "malformed", "wrong-top-level", "wrong-value-type"],
)
def test_unusable_catalog_logs_error_and_uses_emergency_catalog(
    monkeypatch, tmp_path, caplog, content
) -> None:
    with caplog.at_level(logging.ERROR, logger=model_utils.__name__):
        loaded = _load_with(monkeypatch, tmp_path, content)
    assert loaded == {p: [m] for p, m in model_utils._PROVIDER_DEFAULTS.items()}
    assert any("emergency" in r.message for r in caplog.records)


def test_emergency_catalog_cannot_diverge_from_defaults() -> None:
    assert {
        p: [m] for p, m in model_utils._PROVIDER_DEFAULTS.items()
    } == model_utils._EMERGENCY_MODEL_PRESETS
