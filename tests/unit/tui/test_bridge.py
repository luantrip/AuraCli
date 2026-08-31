"""Testes para tui/bridge.py — TEST-NEW-02."""

import contextlib
from queue import Queue
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from aura_cli.application.presentation import PresentationIntent, SurfaceRequest
from aura_cli.application.tools.capability_broker import CapabilityDecision
from aura_cli.tui.bridge import TextualUIManager


def _make_bridge():
    app = MagicMock()
    app.call_from_thread = MagicMock()
    return TextualUIManager(tui_app=app, status_queue=Queue())


class TestTextualUIManagerInit:
    def test_default_init(self):
        bridge = _make_bridge()
        assert bridge.app is not None

    def test_is_initialized_false_by_default(self):
        bridge = _make_bridge()
        assert bridge.is_initialized() is False

    def test_status_queue_stored(self):
        q = Queue()
        bridge = TextualUIManager(tui_app=MagicMock(), status_queue=q)
        assert bridge.status_queue is q

    def test_status_queue_setter(self):
        bridge = _make_bridge()
        q = Queue()
        bridge.status_queue = q
        assert bridge.status_queue is q

    def test_stats_stored(self):
        stats = MagicMock()
        bridge = TextualUIManager(tui_app=MagicMock(), stats=stats)
        assert bridge.stats is stats


class TestDisplayMethods:
    def test_display_response_no_crash(self):
        _make_bridge().display_response("Hello world")

    def test_display_error_no_crash(self):
        _make_bridge().display_error("Something went wrong")

    def test_display_success_no_crash(self):
        _make_bridge().display_success("Done!")

    def test_display_warning_no_crash(self):
        _make_bridge().display_warning("Watch out")

    def test_emit_capability_decision_writes_structured_event(self):
        bridge = _make_bridge()
        decision = CapabilityDecision(
            allowed=False,
            requires_confirmation=False,
            reason="policy denied",
            risk_level="high",
        )

        bridge.emit_capability_decision(
            "delete_file",
            decision,
            task_id="task-1",
            phase="blocked",
        )
        event = bridge.status_queue.get_nowait()

        assert event["type"] == "capability_decision"
        assert event["task_id"] == "task-1"
        assert event["data"]["phase"] == "blocked"
        assert event["data"]["reason"] == "policy denied"
        assert "tool_args" not in event["data"]

    def test_display_info_no_crash(self):
        _make_bridge().display_info("FYI")

    def test_display_shell_output_success(self):
        _make_bridge().display_shell_output("ls -la", True, "file1\nfile2")

    def test_display_shell_output_failure(self):
        _make_bridge().display_shell_output("rm -rf /", False, "Permission denied")

    def test_clear_no_crash(self):
        _make_bridge().clear()

    def test_update_status_no_crash(self):
        _make_bridge().update_status("working", "Processing...")

    def test_print_str(self):
        _make_bridge().print("plain string")

    def test_print_non_str(self):
        _make_bridge().print({"key": "value"})

    def test_display_investigator_progress_completed(self):
        _make_bridge().display_investigator_progress("analysis", "completed")

    def test_display_investigator_progress_other(self):
        _make_bridge().display_investigator_progress("analysis", "running")

    def test_display_investigator_summary(self):
        _make_bridge().display_investigator_summary(
            {
                "summary": {
                    "files_analyzed": 10,
                    "total_lines": 500,
                    "languages": ["Python"],
                }
            }
        )


class TestSyncMetricsAndStop:
    def test_get_sync_metrics_no_manager(self):
        metrics = _make_bridge().get_sync_metrics()
        assert metrics == {"sync_manager": "not_initialized"}

    def test_get_sync_metrics_with_manager(self):
        bridge = _make_bridge()
        bridge._sync_manager = MagicMock()
        bridge._sync_manager.get_metrics.return_value = {"events": 5}
        assert bridge.get_sync_metrics() == {"events": 5}

    def test_stop_no_manager(self):
        _make_bridge().stop()  # must not raise

    def test_stop_with_manager(self):
        bridge = _make_bridge()
        manager = MagicMock()
        bridge._sync_manager = manager
        bridge._init_pending = False
        bridge.stop()
        manager.stop.assert_called_once()
        assert bridge.sync_manager is None
        assert bridge.is_initialized() is False

        bridge.stop()
        manager.stop.assert_called_once()

    def test_sync_manager_property(self):
        bridge = _make_bridge()
        assert bridge.sync_manager is None


class TestPollingBoundary:
    def test_polling_continues_after_unexpected_event_failure(self):
        bridge = _make_bridge()
        bridge.status_queue.put({"type": "first"})
        bridge.status_queue.put({"type": "second"})
        bridge._process_event = MagicMock(
            side_effect=[RuntimeError("projection failed"), None]
        )

        bridge._poll_status_queue()

        assert bridge._process_event.call_count == 2
        assert [call.args[0] for call in bridge._process_event.call_args_list] == [
            {"type": "first"},
            {"type": "second"},
        ]


class TestLegacyInterventionFallback:
    def _open_modal_callback(self, bridge):
        bridge._process_event(
            {
                "type": "human_intervention_request",
                "task_id": "task-1",
                "request_id": "approval-1",
                "prompt": "Executar shell?",
            }
        )
        open_modal = bridge.app.call_from_thread.call_args.args[0]
        bridge.app.push_screen = MagicMock()
        select_dialog = MagicMock(return_value="modal")
        with patch.dict(
            sys.modules,
            {
                "aura_cli.tui.components.shared.dialogs": SimpleNamespace(
                    SelectDialog=select_dialog
                )
            },
        ):
            open_modal()
        return bridge.app.push_screen.call_args.args[1]

    def test_resolver_failure_terminalizes_cancel_without_blocking(self):
        bridge = _make_bridge()
        bridge._intervention_adapter_resolver = MagicMock(
            side_effect=RuntimeError("resolver offline")
        )
        callback = self._open_modal_callback(bridge)

        callback("decline")

        assert bridge._terminal_intervention_responses == [
            {
                "task_id": "task-1",
                "request_id": "approval-1",
                "approved": False,
                "cancelled": True,
                "reason": "resolver_failed",
                "scope": "once",
            }
        ]

    def test_missing_adapter_delivers_terminal_cancel_without_blocking(self):
        bridge = _make_bridge()
        bridge._intervention_adapter_resolver = lambda _task_id: None
        callback = self._open_modal_callback(bridge)

        callback(None)

        assert bridge._terminal_intervention_responses == [
            {
                "task_id": "task-1",
                "request_id": "approval-1",
                "approved": False,
                "cancelled": True,
                "reason": "adapter_unavailable",
                "scope": "once",
            }
        ]

    def test_adapter_delivery_failure_is_contained(self):
        bridge = _make_bridge()
        adapter = MagicMock()
        adapter.receive_response.side_effect = RuntimeError("closed")
        bridge._intervention_adapter_resolver = lambda _task_id: adapter
        callback = self._open_modal_callback(bridge)

        callback("session")
        adapter.receive_response.assert_called_once()
        assert bridge._terminal_intervention_responses[0]["reason"] == "delivery_failed"
        assert bridge._terminal_intervention_responses[0]["cancelled"] is True


class TestProcessEvent:
    def _valid_event(self, event_type="chat_message"):
        return {
            "type": event_type,
            "task_id": "task-1",
            "data": {"sender": "agent", "content": "hello"},
        }

    def test_process_chat_event(self):
        _make_bridge()._process_event(self._valid_event("chat_message"))

    def test_process_task_start_event(self):
        _make_bridge()._process_event(self._valid_event("agi_task_start"))

    def test_process_tool_executing_event(self):
        _make_bridge()._process_event(self._valid_event("tool_executing"))

    def test_process_capability_decision_event(self):
        bridge = _make_bridge()
        bridge._process_event(
            {
                "type": "capability_decision",
                "task_id": "task-1",
                "data": {
                    "tool_name": "delete_file",
                    "allowed": False,
                    "requires_confirmation": False,
                    "risk_level": "critical",
                    "reason": "policy denied",
                    "phase": "blocked",
                    "execution_id": None,
                },
            }
        )
        bridge.app.query_one.assert_called()

    def test_approval_event_updates_task_and_surfaces_correlated_attention(self):
        bridge = _make_bridge()
        bridge._process_event(
            {
                "type": "approval_requested",
                "task_id": "task-1",
                "data": {
                    "status": "awaiting_user",
                    "message": "Run shell?",
                    "request_id": "approval-1",
                    "action": "shell",
                    "resumable": True,
                    "details": {},
                },
            }
        )

        surface_calls = [
            call
            for call in bridge.app.call_from_thread.call_args_list
            if call.args and call.args[0] == bridge.app.present_surface
        ]
        assert len(surface_calls) == 2
        assert surface_calls[0].args[1].intent is PresentationIntent.PROGRESS
        request = surface_calls[1].args[1]
        assert request == SurfaceRequest(
            PresentationIntent.DECISION,
            "Run shell?",
            title="Ação necessária",
            task_id="task-1",
            key="task:task-1/execution:approval-1",
            tone="warning",
        )
        assert bridge.approval_center.pending[0].request_id == "approval-1"

    def test_process_malformed_event_no_crash(self):
        # _process_event should not propagate ValidationError
        bridge = _make_bridge()
        with contextlib.suppress(Exception):
            bridge._process_event({})

    def test_legacy_intervention_opens_scoped_modal_and_delivers_response(self):
        bridge = _make_bridge()
        bridge._process_event(
            {
                "type": "human_intervention_request",
                "task_id": "task-1",
                "request_id": "approval-1",
                "prompt": "Executar shell?",
                "context": {"metadata": {"policy_key": "shell:workspace"}},
            }
        )
        open_modal = bridge.app.call_from_thread.call_args.args[0]
        bridge.app.push_screen = MagicMock()
        select_dialog = MagicMock(return_value="modal")
        with patch.dict(
            sys.modules,
            {
                "aura_cli.tui.components.shared.dialogs": SimpleNamespace(
                    SelectDialog=select_dialog
                )
            },
        ):
            open_modal()
        adapter = MagicMock()
        bridge._intervention_adapter_resolver = lambda _task_id: adapter
        callback = bridge.app.push_screen.call_args.args[1]
        callback("session")

        adapter.receive_response.assert_called_once_with(
            {
                "task_id": "task-1",
                "request_id": "approval-1",
                "approved": True,
                "cancelled": False,
                "reason": None,
                "scope": "session",
            }
        )
