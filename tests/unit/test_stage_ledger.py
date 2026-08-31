from aura_cli.core.agi.stage_ledger import StageLedger


def test_stage_ledger_round_trip(tmp_path):
    ledger = StageLedger("task-1")
    ledger.start("plan").complete(usd_cost=0.12, input_tokens=10, output_tokens=4)
    path = tmp_path / "ledger.json"
    ledger.save(path)
    loaded = StageLedger.load(path)
    assert loaded.summary()["total_cost"] == 0.12
    assert loaded.summary()["output_tokens"] == 4
