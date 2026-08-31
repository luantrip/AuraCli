"""Regression tests for ownership of AuraTUI event subscriptions."""

from unittest.mock import Mock

from aura_cli.tui.app import AuraTUI
from aura_cli.tui.event_subscriptions import bind_tui_events


def test_teardown_releases_only_owned_subscriptions() -> None:
    owned = [Mock(), Mock(), Mock()]
    app = object.__new__(AuraTUI)
    app._event_unsubscribers = owned.copy()

    app._teardown_event_subscriptions()

    for unsubscribe in owned:
        unsubscribe.assert_called_once_with()
    assert app._event_unsubscribers == []


def test_tui_handlers_ignore_non_mapping_payloads() -> None:
    app = object.__new__(AuraTUI)
    app.notify = Mock()
    app._execute_command = Mock()

    app._on_toast_event(None)
    app._on_command_event([])
    app._on_navigate_event("not-a-payload")

    app.notify.assert_not_called()
    app._execute_command.assert_not_called()


def test_binding_owns_only_the_three_application_channels() -> None:
    bus = Mock()
    bus.subscribe.side_effect = [Mock(), Mock(), Mock()]
    host = Mock()

    owned = bind_tui_events(bus, host)

    assert len(owned) == 3
    assert [call.args[0] for call in bus.subscribe.call_args_list] == [
        "tui.toast.show",
        "tui.command.execute",
        "tui.navigate",
    ]
