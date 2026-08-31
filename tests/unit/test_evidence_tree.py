from pathlib import Path

from aura_cli.core.agi.evidence_tree import EvidenceTree


def test_evidence_tree_materializes_and_cleans(tmp_path: Path):
    source = tmp_path / "source.py"
    source.write_text("print('ok')", encoding="utf-8")
    tree = EvidenceTree(tmp_path / "run", "task-1")
    layout = tree.build("Do it", conversation_history=[{"role": "user", "content": "hello"}], relevant_files=[source])
    assert layout.has_task
    assert layout.conversation_chunks == 1
    assert layout.codebase_files == 1
    assert "task.md" in tree.mission_pointer()
    tree.cleanup()
    assert not (tmp_path / "run").exists()
