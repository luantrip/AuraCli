from aura_cli.core.agi.stage_ledger import StageLedger


def test_memory_style_artifact_round_trip(tmp_path):
    ledger = StageLedger("memory-test")
    ledger.start("persist").complete(usd_cost=0.01)
    path = tmp_path / "memory.json"
    ledger.save(path)
    assert StageLedger.load(path).task_id == "memory-test"
