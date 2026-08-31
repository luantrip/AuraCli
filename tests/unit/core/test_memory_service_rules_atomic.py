"""Atomic persistence contracts for learned memory rules."""

import json
from unittest.mock import MagicMock, patch

import pytest

from aura_cli.core.memory.memory_service import LearnedRule, MemoryService


def _service(tmp_path):
    service = MemoryService.__new__(MemoryService)
    service.memory_path = tmp_path
    (tmp_path / "scratchpad").mkdir()
    return service


def test_save_learned_rules_replaces_json_atomically(tmp_path):
    service = _service(tmp_path)
    rules_file = tmp_path / "scratchpad" / "rules.json"
    rules_file.write_text('{"rules": [{"rule": "old"}]}', encoding="utf-8")

    assert (
        service._save_learned_rules(
            [LearnedRule(rule="new", context="ctx", source="agi")]
        )
        is True
    )

    saved = json.loads(rules_file.read_text(encoding="utf-8"))
    assert saved["rules"][0]["rule"] == "new"
    assert not list(rules_file.parent.glob(f".{rules_file.name}.*.tmp"))


def test_create_context_snapshot_writes_metadata_atomically(tmp_path):
    service = _service(tmp_path)
    (tmp_path / "sessions").mkdir()
    service._notebook_service = MagicMock()
    service.notebook_service.create_snapshot.return_value = "snapshot-1"

    result = service.create_context_snapshot(
        [{"role": "user", "content": "hello"}],
        metadata={"source": "test"},
    )

    metadata_file = tmp_path / "sessions" / "snapshot-1_meta.json"
    assert result == "snapshot-1"
    assert json.loads(metadata_file.read_text(encoding="utf-8")) == {"source": "test"}
    assert not list(metadata_file.parent.glob(f".{metadata_file.name}.*.tmp"))


def test_save_learned_rules_keeps_previous_file_when_serialization_fails(tmp_path):
    service = _service(tmp_path)
    rules_file = tmp_path / "scratchpad" / "rules.json"
    previous = '{"rules": [{"rule": "previous"}]}'
    rules_file.write_text(previous, encoding="utf-8")

    with patch("aura_cli.core.memory.memory_service.json.dump", side_effect=TypeError):
        with pytest.raises(TypeError):
            service._save_learned_rules(
                [LearnedRule(rule="new", context="ctx", source="agi")]
            )

    assert rules_file.read_text(encoding="utf-8") == previous
    assert not list(rules_file.parent.glob(f".{rules_file.name}.*.tmp"))
