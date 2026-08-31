"""Atomic text persistence contracts for the Python notebook backend."""

from pathlib import Path
from unittest.mock import patch

import pytest

from aura_cli.core.memory.notebook_service import _atomic_write_text


def test_atomic_write_text_replaces_content_and_cleans_temp_files(tmp_path: Path):
    destination = tmp_path / "index.md"
    destination.write_text("old", encoding="utf-8")

    _atomic_write_text(destination, "new content")

    assert destination.read_text(encoding="utf-8") == "new content"
    assert not list(tmp_path.glob(f".{destination.name}.*.tmp"))


def test_atomic_write_text_preserves_previous_content_when_replace_fails(
    tmp_path: Path,
):
    destination = tmp_path / "index.md"
    destination.write_text("old", encoding="utf-8")

    with patch(
        "aura_cli.core.memory.notebook_service.os.replace",
        side_effect=OSError("replace failed"),
    ):
        with pytest.raises(OSError, match="replace failed"):
            _atomic_write_text(destination, "new content")

    assert destination.read_text(encoding="utf-8") == "old"
    assert not list(tmp_path.glob(f".{destination.name}.*.tmp"))
