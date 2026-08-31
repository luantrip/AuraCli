"""Tests for AuraTUI navigation event adaptation."""

from unittest.mock import patch

from aura_cli.tui.app import AuraTUI


def test_navigation_event_forwards_route_and_params() -> None:
    app = object.__new__(AuraTUI)

    with patch("aura_cli.tui.shell.screen_registry.navigate_route") as navigate:
        app._on_navigate_event({"route_type": "history", "params": {"scope": "all"}})

    navigate.assert_called_once_with(app, "history", scope="all")
