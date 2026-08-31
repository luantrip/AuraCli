"""
In-app overlay dialogs (mounted via ``DialogProvider``).

For **screen-stack** prompts use:
- ``aura_cli.tui.components.shared.dialogs``
- ``aura_cli.tui.shell.prompts`` (``push_confirm`` / ``push_input``)
"""

from aura_cli.tui.widgets.dialogs.base_dialog import (
    BaseDialog,
    DialogProvider,
    DialogResult,
)
from aura_cli.tui.widgets.dialogs.confirm_dialog import ConfirmDialog
from aura_cli.tui.widgets.dialogs.error_dialog import FatalErrorDialog
from aura_cli.tui.widgets.dialogs.input_dialog import InputDialog
from aura_cli.tui.widgets.dialogs.select_dialog import SelectDialog

__all__ = [
    "BaseDialog",
    "ConfirmDialog",
    "DialogProvider",
    "DialogResult",
    "FatalErrorDialog",
    "InputDialog",
    "SelectDialog",
]
