"""Tests for the CLI composition root."""

from pathlib import Path
from unittest.mock import Mock, patch

from aura_cli.cli.runtime import RuntimeServices
from aura_cli.core.di import Services
from aura_cli.core.tools.file_system import get_allowed_base_dir


def test_runtime_services_initializes_critical_services_once(tmp_path: Path) -> None:
    memory_service = Mock()
    session_state = Mock()
    container = Mock()
    tangent_manager = Mock()
    hook_manager = Mock()
    container.resolve.side_effect = lambda service: (
        tangent_manager
        if service == Services.TANGENT_MANAGER
        else hook_manager
        if service == Services.HOOK_MANAGER
        else Mock()
    )
    notebook_service = Mock()
    imagination_manager = Mock()
    checkpoint_manager = Mock()

    with (
        patch("aura_cli.core.di_bootstrap.bootstrap_services") as bootstrap,
        patch("aura_cli.core.di.get_container", return_value=container),
        patch(
            "aura_cli.core.memory.memory_service.get_memory_service",
            return_value=memory_service,
        ) as get_memory,
        patch(
            "aura_cli.core.sessions.session_state.get_session_state",
            return_value=session_state,
        ) as get_session,
        patch(
            "aura_cli.core.memory.notebook_service.get_notebook_service",
            return_value=notebook_service,
        ),
        patch(
            "aura_cli.core.memory.memory_manager.ImaginationManager",
            return_value=imagination_manager,
        ),
        patch(
            "aura_cli.core.checkpoint.CheckpointManager",
            return_value=checkpoint_manager,
        ),
    ):
        services = RuntimeServices.initialize(tmp_path)

    bootstrap.assert_called_once_with()
    assert get_allowed_base_dir() == tmp_path.resolve()
    get_memory.assert_called_once_with(tmp_path.resolve())
    get_session.assert_called_once_with()
    session_state.initialize.assert_called_once_with(tmp_path.resolve())
    assert services.memory_service is memory_service
    assert services.session_state is session_state
    assert services.project_root == tmp_path.resolve()
    assert services.container is container
    assert services.notebook_service is notebook_service
    assert services.imagination_manager is imagination_manager
    assert services.tangent_manager is tangent_manager
    assert services.checkpoint_manager is checkpoint_manager
    assert services.hook_manager is hook_manager
    assert container.override.call_count == 2


def test_runtime_services_does_not_hide_critical_failure(tmp_path: Path) -> None:
    with (
        patch("aura_cli.core.di_bootstrap.bootstrap_services"),
        patch(
            "aura_cli.core.memory.memory_service.get_memory_service",
            side_effect=RuntimeError("memory unavailable"),
        ),
    ):
        try:
            RuntimeServices.initialize(tmp_path)
        except RuntimeError as exc:
            assert str(exc) == "memory unavailable"
        else:
            raise AssertionError("critical initialization failure was hidden")


def test_runtime_services_shutdown_is_idempotent(tmp_path: Path) -> None:
    container = Mock()
    services = RuntimeServices(
        project_root=tmp_path,
        memory_service=Mock(),
        session_state=Mock(),
        notebook_service=Mock(),
        imagination_manager=Mock(),
        tangent_manager=Mock(),
        checkpoint_manager=Mock(),
        hook_manager=Mock(),
        container=container,
        workspace=Mock(),
    )

    services.shutdown()
    services.shutdown()

    container.shutdown.assert_called_once_with()
