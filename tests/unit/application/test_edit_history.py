from datetime import datetime

import pytest

from aura_cli.application.editing import (
    EditOperation,
    create_edit_record,
    summarize_edit_history,
)


def test_edit_record_has_bounded_previews() -> None:
    operation = EditOperation("id", "a.py", "a" * 101, "b" * 101, "edit")

    record = create_edit_record(
        operation,
        now=datetime(2026, 1, 1),
        record_id="record",
    )

    assert record.id == "record"
    assert record.old_content_preview == "a" * 100 + "..."
    assert record.new_content_preview == "b" * 100 + "..."


def test_edit_history_summary_groups_outcomes_and_files() -> None:
    first = create_edit_record(EditOperation("1", "a.py", "a", "b", "one"))
    second = create_edit_record(
        EditOperation("2", "a.py", "b", "c", "two"), success=False
    )

    summary = summarize_edit_history([first, second])

    assert summary == {
        "total_edits": 2,
        "successful_edits": 1,
        "failed_edits": 1,
        "unique_files": 1,
        "edits_per_file": {"a.py": 2},
    }


def test_negative_preview_limit_is_rejected() -> None:
    operation = EditOperation("id", "a.py", "a", "b", "edit")
    with pytest.raises(ValueError, match="cannot be negative"):
        create_edit_record(operation, preview_limit=-1)
