"""Persistent external-tool status projection in the TUI footer."""

from unittest.mock import MagicMock, Mock

import pytest
from textual.app import App, ComposeResult

from aura_cli.application.presentation.external_tools import (
    ExternalToolPhase,
    begin_external_tool,
    transition_external_tool,
)
from aura_cli.tui.app import AuraTUI
from aura_cli.tui.widgets.footer import AuraFooter


class FooterHarness(App[None]):
    """Minimal host for the real footer widget."""

    def compose(self) -> ComposeResult:
        yield AuraFooter(id="footer")


@pytest.mark.asyncio
async def test_footer_renders_external_tool_phase_and_clears_it() -> None:
    app = FooterHarness()
    session = begin_external_tool("external-1", "Paint", "/workspace")
    session = transition_external_tool(session, ExternalToolPhase.LAUNCHING)

    async with app.run_test(size=(100, 8)) as pilot:
        await pilot.pause()
        footer = app.query_one(AuraFooter)
        footer.set_external_tool_session(session)
        label = footer.query_one("#footer-external-tool")

        assert "Paint · abrindo" in label.render().plain
        assert label.has_class("external-tool-launching")

        footer.set_external_tool_session(None)

        assert label.render().plain == ""
        assert not label.has_class("external-tool-launching")


@pytest.mark.asyncio
async def test_aura_app_projects_external_tool_transitions_without_launching() -> None:
    app = AuraTUI(app_loop=MagicMock())

    async with app.run_test(size=(120, 24)) as pilot:
        app._begin_external_session("Paint")
        await pilot.pause()
        label = app.query_one("#footer-external-tool")
        assert "Paint · preparando" in label.render().plain

        app._advance_external_session(ExternalToolPhase.LAUNCHING)
        app._advance_external_session(ExternalToolPhase.ATTACHED)
        await pilot.pause()

        assert "Paint · aberta" in label.render().plain
        assert label.has_class("external-tool-attached")


def test_app_syncs_external_tool_session_to_footer() -> None:
    app = object.__new__(AuraTUI)
    session = begin_external_tool("external-1", "Arquivos", "/workspace")
    footer = Mock()
    app.external_tool_session = session
    app.query_one = Mock(return_value=footer)

    app._sync_external_tool_footer()

    footer.set_external_tool_session.assert_called_once_with(session)
