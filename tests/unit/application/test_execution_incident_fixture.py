import json
from pathlib import Path


def test_realgram_incident_fixture_keeps_all_reproduction_axes() -> None:
    fixture = Path("tests/fixtures/execution_incident/realgram_scenarios.json")
    data = json.loads(fixture.read_text(encoding="utf-8"))

    assert {scenario["id"] for scenario in data["scenarios"]} == {
        "failed_test_claimed_success",
        "mutation_without_tool",
        "delegation_lifecycle",
        "provider_timeout_retry",
    }
    assert data["visual_widths"] == [60, 80, 100, 120, 160]
