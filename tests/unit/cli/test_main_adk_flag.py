"""Startup contract for the ADK feature flag."""

from unittest.mock import Mock, patch

from aura_cli.cli.main import _init_core_services


def test_disabled_adk_is_not_initialized(tmp_path) -> None:
    runtime = Mock(project_root=tmp_path.resolve())

    with (
        patch("aura_cli.cli.main.RuntimeServices.initialize", return_value=runtime),
        patch("aura_cli.core.agents.is_adk_bridge_enabled", return_value=False),
        patch("aura_cli.core.agents.ensure_adk_initialized") as initialize_adk,
        patch("aura_cli.core.nim_integrity.check_nim_integrity", return_value={}),
        patch("aura_cli.core.nim_integrity.log_integrity_summary"),
        patch("aura_cli.application.observability.get_telemetry_coordinator"),
    ):
        _init_core_services(tmp_path)

    initialize_adk.assert_not_called()
