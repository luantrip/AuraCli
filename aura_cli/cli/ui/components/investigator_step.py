"""AuraInvestigatorStep component — individual step status display."""

from typing import Optional

from rich.console import RenderableType
from rich.text import Text

from aura_cli.cli.ui.components.base import ComponentBase
from aura_cli.cli.ui.constants import UIIcons, UIStyles


class AuraInvestigatorStep(ComponentBase):
    """Render the status of an individual investigation step."""

    def render(
        self,
        step_name: str,
        status: str = "pending",
        details: Optional[str] = None,
    ) -> RenderableType:
        """Render a status line for a single step."""
        status_config = {
            "pending": {"icon": UIIcons.IDLE, "color": UIStyles.MUTED, "suffix": ""},
            "running": {
                "icon": UIIcons.LOADING,
                "color": UIStyles.INFO,
                "suffix": "…",
            },
            "completed": {
                "icon": UIIcons.SUCCESS,
                "color": UIStyles.SUCCESS,
                "suffix": "",
            },
            "error": {"icon": UIIcons.ERROR, "color": UIStyles.ERROR, "suffix": ""},
        }

        config = status_config.get(status, status_config["pending"])

        text = Text()
        text.append(f"{config['icon']} ", style=config["color"])
        text.append(step_name, style=UIStyles.LABEL)
        text.append(config["suffix"], style=config["color"])

        if details:
            text.append(f" {details}", style=UIStyles.MUTED)

        return text
