"""Pure decision tests for the Aura TUI controller."""

import pytest

from aura_cli.application.presentation.command_routing import (
    PresentationCommandAction as TUICommandAction,
)
from aura_cli.application.presentation.command_routing import (
    PresentationCommandRouter as AuraTUIController,
)


@pytest.mark.parametrize(
    ("command", "expected"),
    [
        ("/clear", TUICommandAction.CLEAR),
        (" /KEYS ", TUICommandAction.SHORTCUTS),
        ("/tools-menu", TUICommandAction.TOOLS),
        ("/model set x", TUICommandAction.MODEL),
        ("/checkpoint create", TUICommandAction.PASSTHROUGH),
        ("/unknown", TUICommandAction.UNHANDLED),
    ],
)
def test_command_classification(command, expected) -> None:
    assert AuraTUIController().classify_command(command) is expected


def test_agi_selection_is_explicit_and_conservative() -> None:
    controller = AuraTUIController()

    assert controller.should_use_agi_worker("implemente um endpoint")
    assert not controller.should_use_agi_worker("explique este endpoint")
    assert not controller.should_use_agi_worker("/agi implemente um endpoint")
