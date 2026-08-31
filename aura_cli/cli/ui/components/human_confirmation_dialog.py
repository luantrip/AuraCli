"""Human intervention confirmation dialog — minimal visual style."""

import time
from typing import Any, Dict

from rich.console import Group, RenderableType
from rich.text import Text

from aura_cli.application.presentation.cli_visual import SurfaceChrome
from aura_cli.application.presentation.safe_payloads import redact_tool_args
from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.composition.visual_surface import surface_panel
from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.ui.display_facade import get_console
from aura_cli.cli.ui.theme_manager import get_theme_manager
from aura_cli.core.events.human_intervention_events import (
    RISK_CONFIG,
    InterventionRequest,
    RiskLevel,
)


class HumanConfirmationDialog(ComponentBase):
    """Minimalist confirmation dialog (prompt + compact context + controls)."""

    def __init__(self):
        """Initialize the widget."""
        super().__init__()
        self.theme = get_theme_manager()
        self.console = get_console()

    def render(
        self, request: InterventionRequest, show_timer: bool = True
    ) -> RenderableType:
        """Render the confirmation dialog."""
        risk_level = request.context.risk_level
        risk_config: Dict[str, Any] = RISK_CONFIG.get(
            risk_level, RISK_CONFIG[RiskLevel.MEDIUM]
        )
        border_color = str(risk_config["color"])
        dim = self.theme.get_color("muted")

        # Header: single line, minimal
        header = Text()
        header.append(str(risk_config["icon"]), style=border_color)
        header.append(" ", style=border_color)
        header.append(
            request.prompt.strip().split("\n")[0][:60], style=f"dim {border_color}"
        )
        if request.context.tool_name:
            header.append(f"  · {request.context.tool_name}", style=f"dim {dim}")

        body = [header, Text()]

        # Arguments on one line when possible
        if request.context.tool_args:
            args_preview = " ".join(
                f"{k}={str(v)[:20]}"
                for k, v in list(redact_tool_args(request.context.tool_args).items())[
                    :3
                ]
            )
            if len(args_preview) > 70:
                args_preview = args_preview[:67] + "..."
            body.append(Text(f"  {args_preview}", style=f"dim {dim}"))
            body.append(Text())

        if request.context.description:
            body.append(Text(request.context.description, style=f"dim {dim}"))
            body.append(Text())

        if show_timer and request.timeout:
            elapsed = time.time() - request.timestamp
            remaining = max(0, request.timeout - elapsed)
            if remaining > 0:
                body.append(
                    Text(f"{UIIcons.TIMER} {int(remaining)}s", style=f"dim {dim}")
                )
                body.append(Text())

        controls = "  [y] Uma vez  [a] Nesta sessão"
        if request.context.metadata.get("policy_key"):
            controls += "  [p] Salvar política"
        controls += "  [n] Não  [c] Cancelar"
        body.append(Text(controls, style=dim))

        return surface_panel(
            Group(*body),
            border_style=border_color,
            chrome=SurfaceChrome.FOCUS,
            console_width=self.console.width,
        )

    def prompt_user(self, request: InterventionRequest) -> Dict[str, Any]:
        """Display the dialog and wait for user response."""
        from rich.prompt import Prompt

        panel = self.render(request, show_timer=False)
        self.console.print(panel)

        start_time = time.time()

        while True:
            if request.timeout:
                elapsed = time.time() - start_time
                if elapsed >= request.timeout:
                    return {"approved": False, "cancelled": True, "reason": "timeout"}

            try:
                choices = ["y", "Y", "a", "A", "n", "N", "c", "C", "s", "S"]
                if request.context.metadata.get("policy_key"):
                    choices.extend(["p", "P"])
                response = Prompt.ask(
                    f"[{UIStyles.ACCENT}]Confirmar[/{UIStyles.ACCENT}]",
                    choices=choices,
                    default="n",
                    show_choices=False,
                ).lower()

                if response in ["y", "s"]:
                    return {"approved": True, "value": "Sim", "scope": "once"}
                elif response == "a":
                    return {"approved": True, "value": "Sim", "scope": "session"}
                elif response == "p":
                    return {"approved": True, "value": "Sim", "scope": "policy"}
                elif response == "n":
                    return {"approved": False, "value": "Não"}
                elif response == "c":
                    return {
                        "approved": False,
                        "cancelled": True,
                        "reason": "user_cancelled",
                    }

            except KeyboardInterrupt:
                return {"approved": False, "cancelled": True, "reason": "interrupted"}
            except Exception as e:
                self.console.print(f"[red]{UIIcons.ERROR} {e}[/red]")
                continue


class HumanDoubleConfirmationDialog(HumanConfirmationDialog):
    """Double confirmation for critical actions (Safety Lock)."""

    def prompt_user(self, request: InterventionRequest) -> Dict[str, Any]:
        """Display the dialog and wait for user response."""
        first_response = super().prompt_user(request)
        if not first_response.get("approved"):
            return first_response
        self.console.print(
            Text("  Confirmar novamente (ação crítica)", style="dim yellow")
        )
        return super().prompt_user(request)
