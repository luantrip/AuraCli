"""Semantic golden regression tests for the TUI visual system."""

from dataclasses import asdict
import json
from pathlib import Path

import pytest

from aura_cli.application.presentation.visual_acceptance import run_visual_scenario

ROOT = Path(__file__).resolve().parents[3]
SCENARIOS_PATH = ROOT / "tests/fixtures/visual_system/scenarios.json"
GOLDEN_PATH = ROOT / "tests/fixtures/visual_system/golden_frames.json"
VIEWPORTS = ((80, 24), (160, 40), (80, 24), (160, 40))


with SCENARIOS_PATH.open(encoding="utf-8") as scenarios_file:
    SCENARIOS = json.load(scenarios_file)
with GOLDEN_PATH.open(encoding="utf-8") as golden_file:
    GOLDENS = json.load(golden_file)


@pytest.mark.parametrize("scenario_name", sorted(SCENARIOS))
def test_visual_scenario_matches_semantic_golden(scenario_name: str) -> None:
    frames = run_visual_scenario(SCENARIOS[scenario_name], viewports=VIEWPORTS)

    actual = json.loads(
        json.dumps([asdict(frame) for frame in frames], ensure_ascii=False)
    )
    assert actual == GOLDENS[scenario_name]


def test_golden_covers_every_checked_in_scenario() -> None:
    assert set(GOLDENS) == set(SCENARIOS)
    assert all(GOLDENS[name] for name in SCENARIOS)
