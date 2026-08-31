"""Scenario tests for AppLoop.run behavior."""

import inspect
from pathlib import Path
import threading
from types import SimpleNamespace
from unittest.mock import Mock, patch

from aura_cli.cli.app_loop import AppLoop
from tests.runtime_helpers import make_runtime_services


def _make_app_loop():
    """Create AppLoop with mocked heavy dependencies."""
    ui = Mock()
    ui.status_queue = Mock()
    ui.prompt.return_value = "exit"
    app_loop = AppLoop(
        ui=ui,
        stats=Mock(),
        console=Mock(),
        conversation_history=[],
        context_manager=Mock(),
        available_tools={},
        initial_model="auto",
        project_root=Path.cwd(),
        runtime_services=make_runtime_services(Path.cwd()),
    )
    return app_loop, ui


class TestAppLoopRunScenarios:
    """Covers termination paths in the interactive loop."""

    def test_runtime_services_is_a_required_dependency(self):
        parameter = inspect.signature(AppLoop).parameters["runtime_services"]

        assert parameter.default is inspect.Parameter.empty

    def test_constructor_reuses_services_from_composition_root(self):
        """AppLoop must not initialize memory and session a second time."""
        memory_service = Mock(notebook_manager=Mock())
        session_state = Mock()
        workspace = SimpleNamespace(
            memory=memory_service,
            session=session_state,
            context=Mock(),
            imagination=Mock(),
            checkpoint=Mock(),
        )
        runtime_services = SimpleNamespace(
            project_root=Path.cwd().resolve(),
            workspace=workspace,
            memory_service=memory_service,
            session_state=session_state,
            imagination_manager=workspace.imagination,
            tangent_manager=Mock(),
            checkpoint_manager=workspace.checkpoint,
            hook_manager=Mock(),
        )

        app_loop = AppLoop(
            ui=Mock(),
            stats=Mock(),
            console=Mock(),
            conversation_history=[],
            context_manager=Mock(),
            available_tools={},
            initial_model="auto",
            project_root=Path.cwd(),
            runtime_services=runtime_services,
        )

        session_state.initialize.assert_not_called()
        assert app_loop._memory_service is memory_service

    def test_run_exits_immediately_when_shutdown_event_is_set(self):
        """Loop should stop cleanly before prompting user."""
        app_loop, ui = _make_app_loop()
        ev = threading.Event()
        ev.set()
        app_loop.shutdown_event = ev

        with (
            patch("aura_cli.cli.session_lifecycle.register_ui"),
            patch("aura_cli.cli.session_lifecycle.unregister_ui") as unregister_ui,
            patch.object(app_loop, "shutdown") as shutdown,
        ):
            app_loop.run()

        ui.prompt.assert_not_called()
        ui.display_success.assert_called_once()
        shutdown.assert_called_once_with()
        unregister_ui.assert_called_once()

    def test_run_handles_keyboard_interrupt_from_prompt(self):
        """Keyboard interrupt should show warning and finish session."""
        app_loop, ui = _make_app_loop()
        ui.prompt.side_effect = KeyboardInterrupt()

        with (
            patch("aura_cli.cli.session_lifecycle.register_ui"),
            patch("aura_cli.cli.session_lifecycle.unregister_ui"),
            patch.object(app_loop, "shutdown") as shutdown,
        ):
            app_loop.run()

        ui.display_warning.assert_called_once()
        ui.display_success.assert_called_once()
        shutdown.assert_called_once_with()

    def test_run_unregisters_ui_when_shutdown_fails(self):
        """UI registration must be released even if runtime cleanup fails."""
        app_loop, _ = _make_app_loop()

        with (
            patch("aura_cli.cli.session_lifecycle.register_ui"),
            patch("aura_cli.cli.session_lifecycle.unregister_ui") as unregister_ui,
            patch.object(
                app_loop, "shutdown", side_effect=RuntimeError("cleanup failed")
            ),
        ):
            app_loop.run()

        unregister_ui.assert_called_once()
