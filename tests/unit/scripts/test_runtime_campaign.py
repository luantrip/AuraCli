from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

SCRIPT_PATH = (
    Path(__file__).parents[3] / "scripts" / "rea-scripts" / "run_runtime_campaign.py"
)
SPEC = importlib.util.spec_from_file_location("runtime_campaign", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
runtime_campaign = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = runtime_campaign
SPEC.loader.exec_module(runtime_campaign)


def test_cloud_success_requires_expected_output() -> None:
    scenario = runtime_campaign.Scenario(
        "cloud",
        ("chat",),
        cloud=True,
        provider="GROQ_API_KEY",
        expected=("READY",),
    )

    assert runtime_campaign._classify_result(scenario, 0, "READY") == "passed"
    assert runtime_campaign._classify_result(scenario, 0, "empty") == "failed"


def test_known_provider_failure_is_manual() -> None:
    scenario = runtime_campaign.Scenario(
        "cloud",
        ("chat",),
        cloud=True,
        provider="GOOGLE_API_KEY",
        expected=("READY",),
    )

    status = runtime_campaign._classify_result(
        scenario, 1, "NotFoundError: model not found"
    )

    assert status == "manual"


def test_resume_fixture_is_isolated(tmp_path: Path) -> None:
    scenario = runtime_campaign.Scenario(
        "resume",
        ("--resume", "__SESSION_ID__"),
        prepare="resume",
    )
    substitutions = runtime_campaign._prepare_scenario(scenario, tmp_path)

    session_id = substitutions["__SESSION_ID__"]
    session_path = tmp_path / "sessions" / f"{session_id}.json"
    config_path = tmp_path / "config.json"

    assert session_path.is_file()
    assert config_path.is_file()
    assert config_path.stat().st_mode & 0o777 == 0o600
    assert "runtime-fixture" in config_path.read_text(encoding="utf-8")
