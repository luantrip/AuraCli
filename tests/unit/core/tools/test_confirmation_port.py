"""Contracts for the presentation-neutral local confirmation port."""

import pytest

from aura_cli.core.tools import human_intervention_adapter as intervention_module
from aura_cli.core.tools.human_intervention_adapter import (
    configure_local_confirmation_handler,
    request_local_confirmation,
)


@pytest.fixture(autouse=True)
def restore_confirmation_handler():
    original_handler = intervention_module._local_confirmation_handler
    yield
    configure_local_confirmation_handler(original_handler)


def test_confirmation_port_uses_explicit_default_without_adapter() -> None:
    configure_local_confirmation_handler(None)

    assert request_local_confirmation("Continue?", default=False) is False


def test_confirmation_port_delegates_complete_request() -> None:
    observed = {}

    def handler(message, **kwargs):
        observed.update(message=message, **kwargs)
        return True

    configure_local_confirmation_handler(handler)

    assert request_local_confirmation(
        "Continue?", default=False, context="workspace", timeout=12
    )
    assert observed == {
        "message": "Continue?",
        "default": False,
        "context": "workspace",
        "timeout": 12,
    }
