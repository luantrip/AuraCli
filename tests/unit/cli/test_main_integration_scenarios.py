"""Integration-oriented boot scenarios for cli.main."""

from pathlib import Path
from unittest.mock import Mock, patch

from aura_cli.cli.main import _init_core_services, start_interactive_session


class TestMainIntegrationScenarios:
    """Covers boot sequencing and graceful degradation paths."""

    def test_start_interactive_session_runs_onboarding_when_keys_missing(self):
        """If keys are missing, settings flow should run before core init."""
        with (
            patch("aura_cli.cli.main.UIManager") as mock_ui_cls,
            patch("aura_cli.cli.main.Console"),
            patch("aura_cli.cli.main._init_embedding_server"),
            patch("aura_cli.cli.main.check_api_keys", side_effect=[False, True]),
            patch("aura_cli.cli.main.show_settings_menu") as show_settings,
            patch("aura_cli.cli.main.set_environment_for_litellm"),
            patch("aura_cli.cli.main.get_event_bus"),
            patch("aura_cli.cli.main._init_core_services") as init_core,
            patch("aura_cli.cli.main.clear_screen"),
        ):
            ui = Mock()
            mock_ui_cls.return_value = ui

            start_interactive_session()

        show_settings.assert_called_once()
        init_core.assert_called_once()
        ui.display_error.assert_not_called()

    def test_start_interactive_session_exits_when_keys_still_missing(self):
        """If keys remain missing after settings, startup should abort."""
        with (
            patch("aura_cli.cli.main.UIManager") as mock_ui_cls,
            patch("aura_cli.cli.main.Console"),
            patch("aura_cli.cli.main._init_embedding_server"),
            patch("aura_cli.cli.main.check_api_keys", side_effect=[False, False]),
            patch("aura_cli.cli.main.show_settings_menu"),
            patch("aura_cli.cli.main.clear_screen"),
        ):
            ui = Mock()
            mock_ui_cls.return_value = ui

            try:
                start_interactive_session()
                raised = False
            except Exception as exc:
                # Typer raises click-style Exit to stop app bootstrap.
                raised = exc.__class__.__name__ == "Exit"

        assert raised is True
        ui.display_error.assert_called_once()

    def test_init_core_services_continues_when_optional_components_fail(self):
        """Optional component failures should not block AppLoop startup."""
        fake_stats = Mock()
        fake_stats.set_model = Mock()
        fake_event_bus = Mock()
        fake_event_bus.get_queue.return_value = Mock()
        fake_ui = Mock()
        fake_app_loop_instance = Mock()
        fake_config = Mock()
        fake_config.get.return_value = None  # force DEFAULT_MODEL
        runtime_services = Mock(project_root=Path.cwd().resolve())

        with (
            patch(
                "aura_cli.cli.main.RuntimeServices.initialize",
                return_value=runtime_services,
            ),
            patch(
                "aura_cli.core.agents.ensure_adk_initialized",
                side_effect=RuntimeError("adk down"),
            ),
            patch(
                "aura_cli.core.nim_integrity.check_nim_integrity",
                side_effect=RuntimeError("nim down"),
            ),
            patch(
                "aura_cli.application.observability.get_telemetry_coordinator",
                side_effect=RuntimeError("metrics down"),
            ),
            patch("aura_cli.cli.main.get_config_manager", return_value=fake_config),
            patch("aura_cli.cli.main.get_stats", return_value=fake_stats),
            patch("aura_cli.cli.main.get_event_bus", return_value=fake_event_bus),
            patch("aura_cli.cli.main.UIManager", return_value=fake_ui),
            patch("aura_cli.cli.main.display_aura_splash_screen"),
            patch("aura_cli.cli.main.show_onboarding_hint_if_first_run"),
            patch("aura_cli.cli.main.initialize_conversation_history", return_value=[]),
            patch(
                "aura_cli.cli.main.build_runtime_system_note",
                return_value={"role": "system", "content": "note"},
            ),
            patch("aura_cli.cli.main.get_tools_dict", return_value={}),
            patch(
                "aura_cli.cli.main.AppLoop", return_value=fake_app_loop_instance
            ) as mock_app_loop,
        ):
            _init_core_services(Path.cwd())

        fake_app_loop_instance.run.assert_called_once()
        assert mock_app_loop.call_args.kwargs["runtime_services"] is runtime_services
