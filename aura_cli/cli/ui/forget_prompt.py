"""Terminal adapter for the ``/tangent forget`` message picker.

``core/`` cannot import the CLI, so the interactive selector lives here and is
registered into ``core.tangent.manager`` at startup (same injection pattern as
the embedding-server starter).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from aura_cli.cli.ui.prompts import select_dialog

_CANCEL = 0


def select_messages_to_forget(user_messages: List[Dict[str, Any]]) -> Optional[int]:
    """Ask how many recent user messages to forget.

    Returns a count ``>= 1``, or ``None`` when the user cancels. Messages are listed
    from most recent to oldest, so choosing entry *N* forgets the last *N*.
    """
    values: list[tuple[int, str]] = [
        (index, f"[{index}] {info['preview']}")
        for index, info in enumerate(reversed(user_messages), 1)
    ]
    values.append((_CANCEL, "[Cancel]"))
    chosen = select_dialog(
        title="Esquecer mensagens",
        text="Forget up to (and including) the chosen message · most recent first",
        values=values,
        full_screen=False,
    ).run()
    if chosen is None or chosen == _CANCEL:
        return None
    return int(chosen)
