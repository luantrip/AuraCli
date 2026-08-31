from pathlib import Path

from aura_cli.core.skills.founder import (
    EconomicsError,
    analyse_economics,
    analyse_price_sensitivity,
    compile_plan,
    deal_buyers,
    tally_answers,
)
from aura_cli.core.skills.loader import SkillLoader


def _spec() -> dict:
    return {
        "business": "Example",
        "price": 10,
        "variable": [{"cost": 4}],
        "fixed_monthly": [{"cost": 600}],
        "startup": [{"cost": 100}],
        "plan_per_day": 10,
    }


def _customer() -> dict:
    return {
        "business": "Example",
        "target": "busy professionals",
        "segments": [{"name": "core", "income": [30000, 50000], "share": 1}],
        "behaviours": [{"name": "regular", "share": 1}],
        "objections": ["price"],
    }


def test_founder_economics_and_verdict_are_transparent():
    economics = analyse_economics(_spec())
    assert economics["contribution"] == 6
    assert economics["payback_month"] == 1
    result = compile_plan(economics, {"buy_rate": 0.5})
    assert result["verdict"] == "Profitable"
    assert all(result["checks"].values())


def test_founder_rejects_invalid_numbers():
    spec = _spec()
    spec["variable"][0]["cost"] = "bad"
    try:
        analyse_economics(spec)
    except EconomicsError:
        pass
    else:
        raise AssertionError("invalid economics must be rejected")


def test_founder_panel_is_seeded_and_tally_does_not_invent_answers():
    first = deal_buyers(_customer(), count=6, seed=9)
    assert first == deal_buyers(_customer(), count=6, seed=9)
    result = tally_answers(
        [{"id": "P001", "buys": True}, {"id": "P002", "buys": "maybe"}]
    )
    assert result["buys"] == 1
    assert result["answered"] == 1
    assert result["skipped"] == ["P002"]


def test_founder_price_analysis_requires_ordered_answers():
    rows = [(2 + i / 10, 3 + i / 10, 4 + i / 10, 5 + i / 10) for i in range(5)]
    result = analyse_price_sensitivity(rows)
    assert result["answers"] == 5
    assert result["range"] == [2.2, 5.2]


def test_founder_is_discoverable_as_a_native_skill():
    documents = SkillLoader([Path("aura_cli/core/skills")]).load()
    assert any(document.name == "founder" for document in documents)
