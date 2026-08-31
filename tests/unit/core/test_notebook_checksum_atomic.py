"""Atomic notebook checksum persistence contracts."""

import json
from unittest.mock import patch

import pytest

from aura_cli.core.memory.notebook_checksum import NotebookChecksumManager


def test_checksum_save_is_atomic(tmp_path):
    manager = NotebookChecksumManager(tmp_path)

    manager.save_checksum("pagina_1.txt", "checksum-1")

    saved = json.loads((tmp_path / ".checksums.json").read_text(encoding="utf-8"))
    assert saved["pagina_1.txt"]["checksum"] == "checksum-1"
    assert not list(tmp_path.glob("..checksums.json.*.tmp"))


def test_checksum_save_preserves_previous_file_when_replace_fails(tmp_path):
    manager = NotebookChecksumManager(tmp_path)
    checksum_path = tmp_path / ".checksums.json"
    previous = {"pagina_1.txt": {"checksum": "old"}}
    checksum_path.write_text(json.dumps(previous), encoding="utf-8")

    with (
        patch(
            "aura_cli.core.memory.notebook_checksum.os.replace",
            side_effect=OSError("replace failed"),
        ),
        pytest.raises(OSError, match="Failed to persist checksums"),
    ):
        manager._save_checksums({"pagina_1.txt": {"checksum": "new"}})

    assert json.loads(checksum_path.read_text(encoding="utf-8")) == previous
    assert not list(tmp_path.glob("..checksums.json.*.tmp"))
