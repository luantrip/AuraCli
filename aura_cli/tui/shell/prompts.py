"""Push nested modal prompts (confirm / input) on the screen stack."""

from __future__ import annotations

from typing import Callable, Optional, TypeVar

from aura_cli.tui.components.shared.dialogs import ConfirmDialog, InputDialog

T = TypeVar("T")


def push_confirm(
    app,
    *,
    title: str,
    message: str,
    on_result: Callable[[Optional[bool]], None],
    dangerous: bool = False,
    confirm_label: str = "Sim",
    cancel_label: str = "Não",
) -> None:
    app.push_screen(
        ConfirmDialog(
            title=title,
            message=message,
            dangerous=dangerous,
            confirm_label=confirm_label,
            cancel_label=cancel_label,
        ),
        on_result,
    )


def push_input(
    app,
    *,
    title: str,
    message: str = "",
    on_result: Callable[[Optional[str]], None],
    password: bool = False,
    placeholder: str = "",
    default: str = "",
) -> None:
    app.push_screen(
        InputDialog(
            title=title,
            message=message,
            password=password,
            placeholder=placeholder,
            default=default,
        ),
        on_result,
    )
