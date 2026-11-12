"""Tests for the single intent-based CLI ingress.

Contracts:
- RenderCoordinator.present_surface routes a SurfaceRequest by intent to
  the right render primitive.
- display_facade.display_* routes through
present_surface (intent-based) when a UIManager is registered.
"""

from unittest.mock import MagicMock

from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)


def _coordinator():
    from aura_cli.cli.ui.rendering import RenderCoordinator
    from aura_cli.core.stats import get_stats

    rc = RenderCoordinator(MagicMock(), get_stats())
    rc.render_response = MagicMock()
    rc.render_error = MagicMock()
    rc.render_success = MagicMock()
    rc.render_warning = MagicMock()
    rc.render_info = MagicMock()
    rc.status = MagicMock()
    return rc


class TestPresentSurfaceRouting:
    def test_response_routes_to_render_response(self):
        rc = _coordinator()
        rc.present_surface(
            SurfaceRequest(intent=PresentationIntent.RESPONSE, content="hi")
        )
        rc.render_response.assert_called_once()

    def test_error_routes_to_render_error(self):
        rc = _coordinator()
        rc.present_surface(
            SurfaceRequest(intent=PresentationIntent.ERROR, content="boom")
        )
        rc.render_error.assert_called_once_with("boom")

    def test_success_routes_to_render_success(self):
        rc = _coordinator()
        rc.present_surface(
            SurfaceRequest(intent=PresentationIntent.SUCCESS, content="ok")
        )
        rc.render_success.assert_called_once_with("ok")

    def test_warning_routes_to_render_warning(self):
        rc = _coordinator()
        rc.present_surface(
            SurfaceRequest(intent=PresentationIntent.WARNING, content="careful")
        )
        rc.render_warning.assert_called_once_with("careful")

    def test_progress_drives_status_not_panel(self):
        rc = _coordinator()
        rc.present_surface(
            SurfaceRequest(intent=PresentationIntent.PROGRESS, content="working")
        )
        rc.status.set_working.assert_called_once_with("working")
        rc.render_info.assert_not_called()

    def test_information_routes_to_render_info(self):
        rc = _coordinator()
        rc.present_surface(
            SurfaceRequest(intent=PresentationIntent.INFORMATION, content="fyi")
        )
        rc.render_info.assert_called_once_with("fyi")


class TestDisplayFacadeIntentRouting:
    def test_display_methods_route_through_present_surface(self):
        from aura_cli.cli.ui import display_facade

        ui = MagicMock()
        display_facade.register_ui(ui)
        try:
            display_facade.display_error("e")
            display_facade.display_success("s")
            display_facade.display_warning("w")
            display_facade.display_info("i")
        finally:
            display_facade.unregister_ui()

        intents = [c.args[0].intent for c in ui.present_surface.call_args_list]
        assert intents == [
            PresentationIntent.ERROR,
            PresentationIntent.SUCCESS,
            PresentationIntent.WARNING,
            PresentationIntent.INFORMATION,
        ]
        # The content must be forwarded intact.
        contents = [c.args[0].content for c in ui.present_surface.call_args_list]
        assert contents == ["e", "s", "w", "i"]

    def test_falls_back_to_console_without_ui(self):
        from aura_cli.cli.ui import display_facade

        display_facade.unregister_ui()
        # Should not raise even when no UI is registered (console fallback).
        display_facade.display_info("no ui registered")
