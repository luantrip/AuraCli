"""Tests for Paint save decisions without dialogs or filesystem effects."""

from aura_cli.application.paint.save_policy import SaveWarning, plan_format_save


def _plan(format_id: str | None):
    return plan_format_save(
        format_id,
        image_save_formats={"PNG", "WRITE_ONLY"},
        image_open_formats={"PNG"},
        save_disabled_formats={"DISABLED"},
    )


def test_text_and_color_formats_need_no_confirmation() -> None:
    assert _plan("ANSI").warnings == ()
    assert _plan("DISABLED").warnings == ()


def test_plaintext_warns_about_color_and_requires_reload() -> None:
    plan = _plan("PLAINTEXT")

    assert plan.warnings == (SaveWarning.COLOR_LOSS,)
    assert plan.reload_after_save is True


def test_image_warns_about_text_and_requires_reload() -> None:
    plan = _plan("PNG")

    assert plan.warnings == (SaveWarning.TEXT_LOSS,)
    assert plan.reload_after_save is True


def test_write_only_image_preserves_confirmation_order() -> None:
    plan = _plan("WRITE_ONLY")

    assert plan.warnings == (
        SaveWarning.NON_OPENABLE,
        SaveWarning.TEXT_LOSS,
    )
    assert plan.reload_after_save is False
