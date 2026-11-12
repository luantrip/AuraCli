"""The extension system is three layers, documented and enforced by contract.

- application/extensions holds pure contracts (no core/cli/tui imports).
- tui/plugin_manager builds on the Application contract (AuraTUIPluginBase subclasses
  AuraPlugin), not on a parallel definition.
- The plugin guide documents all three surfaces so the public one is unambiguous.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
_PRODUCT_ROOT = _REPO_ROOT / "aura_cli"


def test_extension_contracts_do_not_import_runtime_layers() -> None:
    """application/extensions must stay a pure contract layer."""
    contracts_dir = _PRODUCT_ROOT / "application" / "extensions"
    offenders: list[str] = []
    for source in contracts_dir.rglob("*.py"):
        text = source.read_text(encoding="utf-8")
        for forbidden in (
            "import aura_cli.core",
            "from aura_cli.core",
            "import aura_cli.cli",
            "from aura_cli.cli",
            "import aura_cli.tui",
            "from aura_cli.tui",
        ):
            if forbidden in text:
                offenders.append(f"{source.name}: {forbidden}")
    assert offenders == [], offenders


def test_tui_plugins_build_on_the_shared_contract() -> None:
    """AuraTUIPluginBase reuses the Application AuraPlugin, not a fork."""
    from aura_cli.application.extensions import AuraPlugin
    from aura_cli.tui.plugin_manager import AuraTUIPluginBase

    assert issubclass(AuraTUIPluginBase, AuraPlugin)


def test_plugin_guide_documents_the_three_surfaces() -> None:
    guide = _REPO_ROOT / "docs" / "developer-guides" / "plugins.md"
    text = guide.read_text(encoding="utf-8")
    for surface in (
        "aura_cli.application.extensions",
        "aura_cli.core.extensions",
        "aura_cli.tui.plugin_manager",
    ):
        assert surface in text, surface
    # The guide must name the primary entry point so "which one?" is unambiguous.
    assert "get_plugin_manager" in text
