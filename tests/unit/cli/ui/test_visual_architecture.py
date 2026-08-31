import ast
from pathlib import Path

from aura_cli.application.presentation.cli_visual import SurfaceRole
from aura_cli.cli.ui.surface_catalog import (
    CONSOLE_FACTORY_ALLOWLIST,
    SURFACE_MODULES,
)

UI_ROOT = Path(__file__).parents[4] / "aura_cli" / "cli" / "ui"


def test_flow_decision_and_inspection_roles_are_explicit() -> None:
    assert {SurfaceRole.FLOW, SurfaceRole.DECISION, SurfaceRole.INSPECT} <= set(
        SURFACE_MODULES.values()
    )


def test_leaf_renderers_do_not_create_private_consoles() -> None:
    offenders = []
    for path in UI_ROOT.rglob("*.py"):
        relative = path.relative_to(UI_ROOT).as_posix()
        if relative in CONSOLE_FACTORY_ALLOWLIST:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        creates_console = any(
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "Console"
            and not node.args
            and not node.keywords
            for node in ast.walk(tree)
        )
        if creates_console:
            offenders.append(relative)
    assert not offenders
