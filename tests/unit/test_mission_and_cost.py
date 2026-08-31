from aura_cli.core.agi.mission_builder import build_mission
from aura_cli.core.plugins.cost_tracker import CostTrackerPlugin


def test_mission_builder_creates_pointer(tmp_path):
    pointer = build_mission(tmp_path / "task", "task-1", "Do work")
    assert "context/task.md" in pointer


def test_cost_tracker_consumes_stage_ledger():
    from aura_cli.core.agi.stage_ledger import StageLedger

    ledger = StageLedger("task")
    ledger.start("stage").complete(usd_cost=0.2, input_tokens=3, output_tokens=4)
    tracker = CostTrackerPlugin()
    tracker.consume_stage_ledger(ledger)
    assert tracker.session_cost == 0.2
    assert tracker.session_tokens == 7
