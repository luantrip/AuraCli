"""Tests for dashboard composition surface."""

from unittest.mock import MagicMock

from rich.console import Console

from aura_cli.cli.ui.composition.dashboard_surface import (
    render_dashboard_help,
    render_dashboard_subcommand,
)


def test_render_dashboard_subcommand_help_returns_none():
    console = MagicMock()
    assert render_dashboard_subcommand(console, "help") is None
    console.print.assert_called()


def test_render_dashboard_subcommand_unknown_shows_help():
    console = MagicMock()
    assert render_dashboard_subcommand(console, "not-a-dashboard") is None


def test_render_dashboard_help_prints_panel():
    console = MagicMock()
    render_dashboard_help(console)


def test_unavailable_optional_dashboard_explains_recovery(monkeypatch):
    from aura_cli.cli.ui.composition import dashboard_surface

    console = Console(record=True, width=80)

    def missing_module(_module_path):
        raise ModuleNotFoundError("optional dashboard is not installed")

    monkeypatch.setattr(dashboard_surface.importlib, "import_module", missing_module)

    assert dashboard_surface.render_dashboard_subcommand(console, "memory") is None
    output = console.export_text(clear=False)
    assert "indisponível" in output
    assert "instale/ative a extensão" in output
