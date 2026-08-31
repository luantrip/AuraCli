"""InputManager - Handles user input and prompts.

This module encapsulates all logic related to user input, including
prompt_toolkit integration, key bindings, and large input handling.
"""

from typing import Any, List

from rich.console import Console
from rich.prompt import Prompt

try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.styles import Style

    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

from aura_cli.application.agents.events import ChatMessageEvent
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.layout_contract import layout_for_width
from aura_cli.cli.ui.theme_manager import get_theme_manager
from aura_cli.cli.ui.utils import convert_color_for_prompt_toolkit
from aura_cli.core.llm.model_utils import format_model_display_name
from aura_cli.core.stats import StatsTracker


class InputManager:
    """Manages user input and prompts."""

    def __init__(self, console: Console, stats: StatsTracker, status_queue=None):
        """Initialize the widget."""
        self.console = console
        self.stats = stats
        self.status_queue = status_queue
        self._paste_counter = 0
        self._session: Any = None
        if PROMPT_TOOLKIT_AVAILABLE:
            from aura_cli.core.paths import aura_path

            history_path = aura_path(".aura_history")
            history_path.parent.mkdir(parents=True, exist_ok=True)
            self._session = PromptSession(history=FileHistory(str(history_path)))

    def _build_prompt_style(self) -> Any:
        """Build prompt-toolkit Style from current theme."""
        theme = get_theme_manager()
        return Style.from_dict(
            {
                "primary": f"fg:{convert_color_for_prompt_toolkit(theme.get_color('primary'))}",
                "accent": f"fg:{convert_color_for_prompt_toolkit(theme.get_color('accent'))} bold",
                "label": f"fg:{convert_color_for_prompt_toolkit(theme.get_color('muted'))}",
                "muted": f"fg:{convert_color_for_prompt_toolkit(theme.get_color('muted'))}",
                "success": f"fg:{convert_color_for_prompt_toolkit(theme.get_color('success'))}",
                "warning": f"fg:{convert_color_for_prompt_toolkit(theme.get_color('warning') or '#ffff00')} bold",
            }
        )

    def _handle_large_input(self, user_input: str) -> None:
        """Display collapsed view for large pasted input."""
        self._paste_counter += 1
        try:
            from aura_cli.cli.ui.components.collapsed_text import CollapsedTextDisplay

            collapsed_view = CollapsedTextDisplay().render_minimal(
                user_input,
                label=f"Entrada #{self._paste_counter}",
                for_chat=True,
            )
            self.console.print(collapsed_view)
        except ImportError:
            lines = user_input.splitlines()
            size_kb = len(user_input.encode("utf-8")) / 1024
            self.console.print(
                f"[dim][◇ Entrada #{self._paste_counter} │ {len(lines)} linhas │ {size_kb:.1f} KB][/dim]"
            )

    def _notify_status_queue(self, user_input: str, is_large: bool) -> None:
        """Push user message event to status queue if available."""
        if not self.status_queue:
            return
        metadata: dict = {}
        if is_large:
            lines = user_input.splitlines()
            preview = "\n".join(lines[:3]) + "..."
            size_kb = len(user_input.encode("utf-8")) / 1024
            metadata = {
                "is_large_input": True,
                "preview": preview,
                "stats": f"{size_kb:.1f} KB • {len(lines)} linhas",
            }
        self.status_queue.put(
            ChatMessageEvent.create(
                sender="user",
                content=user_input,
                task_id="global_chat",
                metadata=metadata,
            ).to_dict()
        )

    def prompt(self, tangent_indicator: str = "") -> str:
        """Display only the prompt for user input.

        Args:
            tangent_indicator: Optional tangent mode indicator (e.g., "↯")
        """
        try:
            if PROMPT_TOOLKIT_AVAILABLE:
                from aura_cli.cli.ui.command_completer import CommandCompleter
                from aura_cli.cli.ui.key_bindings import create_key_bindings

                bindings = create_key_bindings()
                completer = CommandCompleter()
                style = self._build_prompt_style()
                layout = layout_for_width(self.console.width)

                prompt_tuples: List[Any] = []
                if tangent_indicator:
                    prompt_tuples.append(("class:warning", f"{tangent_indicator} "))
                prompt_tuples.extend([("class:accent", f"{layout.prompt_symbol} ")])
                if self.stats.skip_confirmations:
                    prompt_tuples.extend(
                        [("", " "), ("class:success", "(sem confirmação)")]
                    )

                _toolbar_cache = [None, 0.0, self.console.width]

                def get_bottom_toolbar():
                    import time as _time

                    # Cache toolbar for 5s to avoid lag from psutil/config during typing
                    now = _time.monotonic()
                    if (
                        _toolbar_cache[0] is not None
                        and _toolbar_cache[2] == self.console.width
                        and (now - _toolbar_cache[1]) < 5.0
                    ):
                        return _toolbar_cache[0]

                    import os

                    from aura_cli.core.config import config_manager
                    from aura_cli.core.llm.model_utils import DEFAULT_MODEL

                    model = config_manager.get("default_model", DEFAULT_MODEL)
                    model_name = format_model_display_name(model)
                    layout = layout_for_width(self.console.width)
                    try:
                        cwd = os.getcwd()
                        cwd_name = (os.path.basename(cwd) or cwd) or "—"
                        cwd_name = layout.truncate_label(cwd_name)
                    except (OSError, RuntimeError):
                        cwd_name = "—"
                    segments = [
                        ("class:primary", f" {UIIcons.AURA} Aura "),
                        ("class:muted", "│"),
                        (
                            "class:accent",
                            f" {layout.fit_inline(model_name, reserve=24)} ",
                        ),
                        ("class:muted", "│"),
                        ("class:label", f" {cwd_name} "),
                    ]
                    if self.stats.skip_confirmations:
                        segments.extend(
                            [("class:muted", "│"), ("class:success", " ✦ Automático ")]
                        )
                    _toolbar_cache[0] = segments
                    _toolbar_cache[1] = now
                    _toolbar_cache[2] = self.console.width
                    return segments

                user_input = (
                    self._session.prompt(
                        prompt_tuples,
                        key_bindings=bindings,
                        style=style,
                        completer=completer,
                        complete_while_typing=True,
                        bottom_toolbar=get_bottom_toolbar,
                        refresh_interval=5.0,
                    )
                    or ""
                )

                if user_input and user_input.startswith("/"):
                    completer.add_to_history(user_input)
            else:
                layout = layout_for_width(self.console.width)
                prompt_text = (
                    f"[{UIStyles.ACCENT}]{layout.prompt_symbol} [/{UIStyles.ACCENT}]"
                )
                if self.stats.skip_confirmations:
                    prompt_text += (
                        f" [{UIStyles.SUCCESS}](sem confirmação)[/{UIStyles.SUCCESS}]"
                    )
                user_input = Prompt.ask(prompt_text) or ""

            user_input = user_input.strip("\r\n") if user_input else ""

            is_large_input = len(user_input) > 500 or user_input.count("\n") > 10
            if is_large_input and user_input:
                self._handle_large_input(user_input)

            self._notify_status_queue(user_input, is_large_input)
            return user_input or ""
        except (EOFError, KeyboardInterrupt):
            raise
        except Exception as e:
            from aura_cli.core.logger import get_logger

            get_logger(__name__).error(f"Error in prompt: {e}", exc_info=True)
            return ""
