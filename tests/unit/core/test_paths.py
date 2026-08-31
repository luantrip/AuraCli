"""Tests for configurable Aura data paths."""

from pathlib import Path

import pytest

from aura_cli.application.artifacts import ArtifactLayout as ApplicationArtifactLayout
from aura_cli.core.paths import ArtifactLayout, aura_path, get_aura_home


def test_aura_home_defaults_to_user_directory(monkeypatch):
    monkeypatch.delenv("AURA_HOME", raising=False)

    assert get_aura_home() == Path.home() / ".aura"


def test_aura_home_can_be_isolated(monkeypatch, tmp_path):
    isolated_home = tmp_path / "aura-data"
    monkeypatch.setenv("AURA_HOME", str(isolated_home))

    assert get_aura_home() == isolated_home.resolve()
    assert (
        aura_path("cache", "analysis") == isolated_home.resolve() / "cache" / "analysis"
    )


def test_core_reexports_canonical_artifact_layout():
    assert ArtifactLayout is ApplicationArtifactLayout


def test_project_artifacts_are_scoped_below_dot_aura(tmp_path):
    assert ArtifactLayout(tmp_path).project("notebooks", "page.md") == (
        tmp_path / ".aura" / "notebooks" / "page.md"
    )


def test_project_root_can_be_isolated_by_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("AURA_PROJECT_ROOT", str(tmp_path))

    assert ArtifactLayout().project("cache") == tmp_path / ".aura" / "cache"


def test_explicit_project_root_wins_over_environment_isolation(monkeypatch, tmp_path):
    isolated_root = tmp_path / "isolated"
    explicit_root = tmp_path / "real-project"
    monkeypatch.setenv("AURA_PROJECT_ROOT", str(isolated_root))

    assert ArtifactLayout(explicit_root).project("cache") == (
        explicit_root / ".aura" / "cache"
    )


@pytest.mark.parametrize("part", ["../escape", "/absolute"])
def test_artifact_layout_rejects_paths_outside_its_root(tmp_path, part):
    with pytest.raises(ValueError, match="relative and contained"):
        ArtifactLayout(tmp_path).project(part)
