"""UI contract tests for the tools catalog entrypoint."""

from __future__ import annotations

from unittest.mock import patch

from rich.console import Console

from aura_cli.cli.commands import agents


def test_handle_tools_uses_open_catalog_surfaces() -> None:
    console = Console(record=True, width=100)
    with patch.object(agents, "Console", return_value=console):
        agents.handle_tools()

    output = console.export_text()
    assert "AGI Tools" in output
    assert "Ops Tools" in output
    assert "╭" not in output
    assert "╰" not in output
