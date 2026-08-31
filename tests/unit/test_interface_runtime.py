"""Tests for the adapter composition root."""

from types import SimpleNamespace

import pytest

from aura_cli.interface_runtime import launch_textual_interface


def test_launch_textual_interface_restores_cli_ui_after_failure(monkeypatch) -> None:
    original_ui = SimpleNamespace(status_queue=object())
    app_loop = SimpleNamespace(ui=original_ui, stats=object())

    class FailingApp:
        def __init__(self, *, app_loop) -> None:
            self.app_loop = app_loop

        def run(self) -> None:
            raise RuntimeError("boom")

    class Bridge:
        def __init__(
            self, app, *, status_queue, stats, intervention_adapter_resolver
        ) -> None:
            self.app = app
            self.intervention_adapter_resolver = intervention_adapter_resolver

    monkeypatch.setattr("aura_cli.tui.app.AuraTUI", FailingApp)
    monkeypatch.setattr("aura_cli.tui.bridge.TextualUIManager", Bridge)

    with pytest.raises(RuntimeError, match="boom"):
        launch_textual_interface(app_loop)

    assert app_loop.ui is original_ui
