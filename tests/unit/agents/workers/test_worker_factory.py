"""Tests for worker factory functions.

Tests cover creation and registration of AgiWorker and OpsWorker threads.
"""

from pathlib import Path
import threading
from unittest.mock import Mock, patch

import pytest

from aura_cli.cli.utils.worker_factory import (
    create_agi_worker_thread,
    create_ops_worker_thread,
)
from aura_cli.cli.utils.worker_readiness import WorkerReadinessError


class TestAgiWorkerFactory:
    """Test suite for create_agi_worker_thread."""

    @patch("aura_cli.cli.utils.worker_factory.get_event_bus")
    @patch("aura_cli.cli.utils.worker_factory.get_tools_dict")
    @patch("aura_cli.cli.utils.worker_factory.get_thread_manager")
    def test_create_agi_worker_thread(
        self, mock_thread_manager, mock_tools, mock_event_bus
    ):
        """Test creating AGI worker thread."""
        # Setup mocks
        mock_queue = Mock()
        mock_event_bus.return_value.get_queue.return_value = mock_queue
        mock_tools.return_value = {"read_file": Mock(), "write_file": Mock()}

        mock_thread = Mock(spec=threading.Thread)
        mock_thread.name = "test_thread"
        mock_manager = Mock()
        mock_manager.register_thread.return_value = mock_thread
        mock_thread_manager.return_value = mock_manager

        # Execute
        api_keys = {"GOOGLE_API_KEY": "test_key"}
        agi_worker, thread = create_agi_worker_thread(
            objective="Test objective",
            model="gemini/gemini-2.0-flash-exp",
            api_keys=api_keys,
            headless=True,
            project_root=Path.cwd(),
            delegation_payload={
                "source": "general_chat",
                "primary_request": "Test objective",
            },
            shutdown_timeout=30.0,
        )

        # Verify
        assert agi_worker is not None
        assert thread is not None
        assert thread == mock_thread
        assert agi_worker.delegation_payload["source"] == "general_chat"
        mock_manager.register_thread.assert_called_once()

    @patch("aura_cli.cli.utils.worker_factory.get_event_bus")
    @patch("aura_cli.cli.utils.worker_factory.get_tools_dict")
    @patch("aura_cli.cli.utils.worker_factory.get_thread_manager")
    def test_create_agi_worker_thread_defaults(
        self, mock_thread_manager, mock_tools, mock_event_bus
    ):
        """Test creating AGI worker with default parameters."""
        mock_queue = Mock()
        mock_event_bus.return_value.get_queue.return_value = mock_queue
        mock_tools.return_value = {}

        mock_thread = Mock(spec=threading.Thread)
        mock_manager = Mock()
        mock_manager.register_thread.return_value = mock_thread
        mock_thread_manager.return_value = mock_manager

        api_keys = {"GOOGLE_API_KEY": "test_key"}
        agi_worker, thread = create_agi_worker_thread(
            objective="Test", model="auto", api_keys=api_keys
        )

        assert agi_worker is not None
        assert thread is not None

    @patch("aura_cli.cli.utils.worker_factory.get_thread_manager")
    def test_missing_agi_credential_does_not_create_thread(
        self, mock_thread_manager, tmp_path
    ):
        with pytest.raises(WorkerReadinessError) as raised:
            create_agi_worker_thread(
                objective="Test",
                model="gpt-4",
                api_keys={},
                headless=True,
                project_root=tmp_path,
            )

        assert raised.value.report.code == "configuration"
        mock_thread_manager.assert_not_called()


class TestOpsWorkerFactory:
    """Test suite for create_ops_worker_thread."""

    @patch("aura_cli.cli.utils.worker_factory.get_event_bus")
    @patch("aura_cli.cli.utils.worker_factory.get_thread_manager")
    def test_create_ops_worker_thread(self, mock_thread_manager, mock_event_bus):
        """Test creating Ops worker thread."""
        mock_queue = Mock()
        mock_event_bus.return_value.get_queue.return_value = mock_queue

        mock_thread = Mock(spec=threading.Thread)
        mock_thread.name = "test_thread"
        mock_manager = Mock()
        mock_manager.register_thread.return_value = mock_thread
        mock_thread_manager.return_value = mock_manager

        api_keys = {"GOOGLE_API_KEY": "test_key"}
        ops_worker, thread = create_ops_worker_thread(
            task="Test task",
            model="gemini/gemini-2.0-flash-exp",
            api_keys=api_keys,
            mode="git",
            headless=True,
            delegation_payload={
                "source": "general_chat",
                "primary_request": "Test task",
            },
            shutdown_timeout=30.0,
        )

        assert ops_worker is not None
        assert thread is not None
        assert thread == mock_thread
        assert ops_worker.delegation_payload["source"] == "general_chat"
        mock_manager.register_thread.assert_called_once()

    @patch("aura_cli.cli.utils.worker_factory.get_thread_manager")
    def test_missing_ops_credential_does_not_create_thread(
        self, mock_thread_manager, tmp_path
    ):
        with pytest.raises(WorkerReadinessError) as raised:
            create_ops_worker_thread(
                task="Test",
                model="gpt-4",
                api_keys={},
                headless=True,
                project_root=tmp_path,
            )

        assert raised.value.report.code == "configuration"
        mock_thread_manager.assert_not_called()

    @patch("aura_cli.cli.utils.worker_factory.get_event_bus")
    @patch("aura_cli.cli.utils.worker_factory.get_thread_manager")
    def test_create_ops_worker_thread_defaults(
        self, mock_thread_manager, mock_event_bus
    ):
        """Test creating Ops worker with default parameters."""
        mock_queue = Mock()
        mock_event_bus.return_value.get_queue.return_value = mock_queue

        mock_thread = Mock(spec=threading.Thread)
        mock_manager = Mock()
        mock_manager.register_thread.return_value = mock_thread
        mock_thread_manager.return_value = mock_manager

        api_keys = {"GOOGLE_API_KEY": "test_key"}
        ops_worker, thread = create_ops_worker_thread(
            task="Test", model="auto", api_keys=api_keys
        )

        assert ops_worker is not None
        assert thread is not None

    @patch("aura_cli.cli.utils.worker_factory.get_event_bus")
    @patch("aura_cli.cli.utils.worker_factory.get_thread_manager")
    def test_create_ops_worker_different_modes(
        self, mock_thread_manager, mock_event_bus
    ):
        """Test creating Ops worker with different modes."""
        mock_queue = Mock()
        mock_event_bus.return_value.get_queue.return_value = mock_queue

        mock_thread = Mock(spec=threading.Thread)
        mock_manager = Mock()
        mock_manager.register_thread.return_value = mock_thread
        mock_thread_manager.return_value = mock_manager

        api_keys = {"GOOGLE_API_KEY": "test_key"}

        for mode in ["git", "docker", "general"]:
            ops_worker, _thread = create_ops_worker_thread(
                task="Test", model="auto", api_keys=api_keys, mode=mode
            )
            assert ops_worker.mode == mode
