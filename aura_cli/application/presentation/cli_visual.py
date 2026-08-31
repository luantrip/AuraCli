"""Presentation-neutral visual policy for the Rich CLI."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CliDensity(str, Enum):
    COMPACT = "compact"
    NORMAL = "normal"
    WIDE = "wide"


class SurfaceChrome(str, Enum):
    FLOW = "flow"
    GROUP = "group"
    FOCUS = "focus"


class SurfaceRole(str, Enum):
    FLOW = "flow"
    DECISION = "decision"
    INSPECT = "inspect"
    OPTIONAL = "optional"
    LEGACY = "legacy"


@dataclass(frozen=True)
class CliVisualPlan:
    width: int
    density: CliDensity
    group_padding: tuple[int, int]
    result_preview_lines: int
    visible_operations: int
    show_metadata: bool
    dashboard_columns: bool


def decide_cli_visual(width: int) -> CliVisualPlan:
    """Return one deterministic density plan for a console width."""
    if not isinstance(width, int):
        width = 80
    width = max(width, 1)
    if width < 80:
        return CliVisualPlan(width, CliDensity.COMPACT, (0, 0), 1, 3, False, False)
    if width < 120:
        return CliVisualPlan(width, CliDensity.NORMAL, (0, 1), 3, 5, True, False)
    return CliVisualPlan(width, CliDensity.WIDE, (0, 1), 6, 8, True, True)


CLI_LABELS = {
    "operations": "Operações",
    "result": "Resultado",
    "output": "Saída",
    "parallel_work": "Trabalho paralelo",
    "validation": "Validação",
    "running": "Em execução",
    "completed": "Concluído",
    "failed": "Falhou",
}


def cli_label(key: str) -> str:
    """Resolve public UI vocabulary from one catalog."""
    try:
        return CLI_LABELS[key]
    except KeyError as error:
        raise ValueError(f"Unknown CLI label: {key}") from error


__all__ = [
    "CLI_LABELS",
    "CliDensity",
    "CliVisualPlan",
    "SurfaceChrome",
    "SurfaceRole",
    "cli_label",
    "decide_cli_visual",
]
