"""Token Usage Details Modal Screen."""

from __future__ import annotations

from typing import Any, Dict, Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Static

from aura_cli.tui.services.token_usage_snapshot import TokenUsageSnapshot
from aura_cli.tui.shell.base_modal import BaseAuraModalScreen


class TokenUsageScreen(BaseAuraModalScreen[None]):
    """Modal overlay displaying context and token usage stats."""

    TITLE = "Contexto"
    SHOW_FOOTER_CLOSE = False
    MODAL_ROOT_ID = "token_usage_modal"

    DEFAULT_CSS = """
    TokenUsageScreen {
        align: center middle;
        background: rgba(0, 0, 0, 0.7);
    }

    TokenUsageScreen #token_usage_modal {
        width: 68;
        height: auto;
        padding: 1 2;
        background: $surface;
        border: round $primary;
    }

    TokenUsageScreen #token_usage_dialog {
        width: 100%;
        height: auto;
        padding: 0;
        background: transparent;
        border: none;
    }
    """

    def __init__(
        self,
        snapshot: Optional[TokenUsageSnapshot] = None,
        *,
        used_tokens: int = 0,
        total_tokens: int = 500_000,
        model_name: str = "aura",
        breakdown: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
        id: Optional[str] = None,
        classes: Optional[str] = None,
    ) -> None:
        super().__init__(name=name, id=id, classes=classes)
        if snapshot is None:
            bd = breakdown or {}
            snapshot = TokenUsageSnapshot(
                used_tokens=used_tokens,
                total_tokens=total_tokens,
                model_name=model_name,
                prompt_tokens=int(bd.get("prompt_tokens", 0)),
                completion_tokens=int(bd.get("completion_tokens", 0)),
            )
        self.snapshot = snapshot

    def compose_body(self) -> ComposeResult:
        with Container(id="token_usage_dialog"):
            yield Static(self._build_content())

    def _build_content(self) -> Text:
        s = self.snapshot
        total_tokens = max(0, s.total_tokens)
        used_tokens = max(0, s.used_tokens)
        pct = min(100.0, (used_tokens / total_tokens) * 100) if total_tokens else 0.0
        text = Text()

        text.append(
            f"{used_tokens / 1000:.1f}k / {total_tokens / 1000:.0f}k tokens ({pct:.2f}%)\n",
            style="bold cyan",
        )
        text.append(f"{s.model_name}\n\n", style="dim white")

        if s.prompt_tokens or s.completion_tokens:
            text.append(
                f"◆ Tokens de prompt       {s.prompt_tokens / 1000:.1f}k\n",
                style="white",
            )
            text.append(
                f"◆ Tokens de resposta     {s.completion_tokens / 1000:.1f}k\n\n",
                style="white",
            )

        filled_count = int((pct / 100) * 40)
        empty_count = 40 - filled_count
        gauge = "◆ " * filled_count + "◇ " * empty_count
        text.append(f"{gauge.strip()}\n\n", style="bold purple")

        if s.tool_definitions_count:
            text.append(
                f"◆ Definições de tools     · {s.tool_definitions_count} tools\n",
                style="cyan",
            )
        if s.skills_count:
            text.append(
                f"◆ Skills                 · {s.skills_count}\n",
                style="cyan",
            )
        if s.mcp_server_count:
            text.append(
                f"◆ Servidores MCP         · {s.mcp_server_count}\n",
                style="cyan",
            )
        if s.tool_definitions_count or s.skills_count or s.mcp_server_count:
            text.append("\n", style="")

        remaining = max(0, total_tokens - used_tokens)
        text.append(
            f"◇ Disponível             ~{remaining / 1000:.0f}k tokens\n\n",
            style="dim white",
        )

        if s.message_count or s.tool_call_count:
            text.append(
                f"Mensagens: {s.message_count} · Tool calls: {s.tool_call_count}\n\n",
                style="dim white",
            )

        for line in s.extra_lines:
            text.append(f"{line}\n", style="dim white")

        text.append(
            "Esc / Enter: fechar  |  ←: recolher",
            style="bold white",
        )

        return text

    def on_key(self, event) -> None:
        if event.key in ("escape", "enter", "left"):
            self.action_close_modal()
