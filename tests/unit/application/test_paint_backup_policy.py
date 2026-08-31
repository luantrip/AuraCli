"""Tests for headless Paint backup decisions."""

from aura_cli.application.paint.backup_policy import (
    BackupDecision,
    backup_path,
    decide_backup,
)


def test_backup_decision_distinguishes_skip_defer_and_save() -> None:
    assert (
        decide_backup(saved_action_count=2, current_action_count=2, has_preview=False)
        is BackupDecision.SKIP
    )
    assert (
        decide_backup(saved_action_count=1, current_action_count=2, has_preview=True)
        is BackupDecision.DEFER_UNTIL_PREVIEW_ENDS
    )
    assert (
        decide_backup(saved_action_count=1, current_action_count=2, has_preview=False)
        is BackupDecision.SAVE
    )


def test_backup_path_replaces_ansi_suffix_and_numbers_sessions(tmp_path) -> None:
    target = backup_path(
        file_path="drawing.ANS",
        backup_folder=str(tmp_path),
        untitled_name="Untitled",
        session_number=3,
    )

    assert target == tmp_path / "drawing.3.ans~"


def test_untitled_backup_uses_supplied_localized_name(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    target = backup_path(
        file_path=None,
        backup_folder=None,
        untitled_name="Sem título",
    )

    assert target == tmp_path / "Sem título.ans~"
