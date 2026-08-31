"""Deterministic state contracts for loading widgets."""

from aura_cli.tui.widgets.loading import AuraLoadingIndicator, AuraProgressBar


def test_loading_spinner_frame_index_is_instance_local() -> None:
    first = AuraLoadingIndicator()
    second = AuraLoadingIndicator()

    first._frame_index = 2

    assert first._frame_index == 2
    assert second._frame_index == 0


def test_progress_bar_set_progress_clamps_to_supported_range() -> None:
    progress = AuraProgressBar()

    progress.set_progress(-5)
    assert progress.progress == 0

    progress.set_progress(150)
    assert progress.progress == 100
