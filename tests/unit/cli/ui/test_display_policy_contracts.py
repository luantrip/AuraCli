"""Display-policy contracts (PE-G*) — see docs/REFATORACAO/07-politica-de-exibicao.md.

These ratchets enforce the display policy that already exists in the codebase so
that code agents cannot silently re-introduce visual pollution. They are
*ratchets*: the current amount of bypass is frozen as a baseline and must only
shrink. New bypass fails CI immediately.

As sub-lote 3 migrates modules behind the single ``present_surface`` funnel,
lower the baselines below (never raise them).
"""

from __future__ import annotations

import ast
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
PRODUCT_ROOT = REPOSITORY_ROOT / "aura_cli"
CLI_ROOT = PRODUCT_ROOT / "cli"
UI_ROOT = CLI_ROOT / "ui"


def _non_ui_cli_sources() -> list[Path]:
    """CLI modules outside the ui/ materializer layer.

    The ui/ layer legitimately owns Rich rendering; everything else (commands,
    top-level handlers, onboarding) must not instantiate its own Console — it
    should use the shared funnel console (display_facade.get_console) or route
    through present_surface.
    """
    return sorted(
        p
        for p in CLI_ROOT.rglob("*.py")
        if UI_ROOT not in p.parents and "workers" not in p.parts
    )


def _instantiates_console(source: Path) -> bool:
    """True if the module constructs a bare ``Console()`` (own private console)."""
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    return any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Console"
        for node in ast.walk(tree)
    )


# --- PE-G1: no private Console outside the funnel (frozen ratchet) ---

# Files that still instantiate their own Console today, bypassing the shared
# funnel console. This set must only SHRINK as modules are migrated.
# Fully migrated 2026-11-03: no non-ui CLI module instantiates a private
# Console anymore. The baseline is now EMPTY — this is a hard zero-tolerance
# contract. Any new private Console() in cli/ (outside ui/ and workers/) fails.
_PRIVATE_CONSOLE_BASELINE: set[str] = set()


def _files_instantiating_console() -> set[str]:
    return {
        source.relative_to(PRODUCT_ROOT).as_posix()
        for source in _non_ui_cli_sources()
        if _instantiates_console(source)
    }


def test_no_new_private_console_in_cli() -> None:
    """PE-G1: no NEW non-ui CLI module may instantiate its own Console.

    Existing offenders are frozen in _PRIVATE_CONSOLE_BASELINE and migrated
    behind the funnel over time. A new file creating a private Console — or a
    migrated file regressing — fails here.
    """
    current = _files_instantiating_console()
    new_offenders = sorted(current - _PRIVATE_CONSOLE_BASELINE)
    assert new_offenders == [], (
        "New private Console() detected (use display_facade.get_console() or "
        f"present_surface instead): {new_offenders}"
    )


def test_private_console_baseline_only_shrinks() -> None:
    """Migrated files must be removed from the baseline to tighten the ratchet."""
    current = _files_instantiating_console()
    stale = sorted(_PRIVATE_CONSOLE_BASELINE - current)
    assert stale == [], (
        "These files no longer create a private Console — remove them from "
        f"_PRIVATE_CONSOLE_BASELINE to tighten the ratchet: {stale}"
    )


# --- PE-G2: bounded number of dashboard modules (frozen ratchet) ---

# Dashboard modules present today. Collapsing them (sub-lote 3) must REMOVE
# entries; adding a new dashboard must fail. Measured 2026-11-03: 8 modules.
_DASHBOARD_BASELINE = {
    "application/presentation/dashboard_query.py",
    "application/presentation/live_dashboard.py",
    "cli/ui/advanced/agent_dashboard.py",
    "cli/ui/components/layout/interactive_dashboard.py",
    "cli/ui/composition/dashboard_surface.py",
    "cli/ui/live_dashboard.py",
    "cli/utils/dashboard_helper.py",
    "core/ops_tools/monitoring/dashboard.py",
}


def _dashboard_modules() -> set[str]:
    return {
        p.relative_to(PRODUCT_ROOT).as_posix()
        for p in PRODUCT_ROOT.rglob("*dashboard*.py")
    }


def test_no_new_dashboard_modules() -> None:
    """PE-G2: no NEW dashboard module may be introduced.

    The display budget allows at most the dashboards that already exist; the
    goal is to collapse them onto one surface, not add more.
    """
    current = _dashboard_modules()
    new_dashboards = sorted(current - _DASHBOARD_BASELINE)
    assert new_dashboards == [], (
        "New dashboard module(s) detected — consolidate onto the existing "
        f"dashboard surface instead: {new_dashboards}"
    )


def test_dashboard_baseline_only_shrinks() -> None:
    """Removed dashboards must be dropped from the baseline to tighten it."""
    current = _dashboard_modules()
    stale = sorted(_DASHBOARD_BASELINE - current)
    assert stale == [], (
        "These dashboard modules no longer exist — remove them from "
        f"_DASHBOARD_BASELINE: {stale}"
    )
