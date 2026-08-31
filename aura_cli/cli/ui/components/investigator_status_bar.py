"""
Componente AuraInvestigatorStatusBar - Barra de status compacta no footer.
"""

from rich.console import RenderableType
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UIStyles


class AuraInvestigatorStatusBar(ComponentBase):
    """Compact component to display investigator status in the footer."""

    def render(
        self,
        status: str = "idle",
        current_step: str = "",
    ) -> RenderableType:
        """Render a compact status bar."""
        status_config = {
            "idle": {
                "icon": UIIcons.SEARCH,
                "color": UIStyles.MUTED,
                "label": "Analisador de codebase",
            },
            "running": {
                "icon": UIIcons.SEARCH,
                "color": UIStyles.INFO,
                "label": "Analisando codebase...",
            },
            "completed": {
                "icon": UIIcons.SUCCESS,
                "color": UIStyles.SUCCESS,
                "label": "Análise Concluída",
            },
            "error": {
                "icon": UIIcons.ERROR,
                "color": UIStyles.ERROR,
                "label": "Erro na Análise",
            },
        }

        config = status_config.get(status, status_config["idle"])

        text = Text()
        text.append(f"{config['icon']} ", style=config["color"])
        text.append(config["label"], style=UIStyles.LABEL)

        if current_step and status == "running":
            text.append(" | ", style=UIStyles.MUTED)
            text.append(current_step, style=UIStyles.PRIMARY)

        return text
