"""Tests for tester_worker.py - TesterWorker for adversarial code validation."""

import queue
from unittest.mock import patch

from aura_cli.cli.workers.tester_worker import TesterWorker, run_adversarial_validation


class TestTesterWorker:
    """Test suite for TesterWorker."""

    def test_initialization(self):
        """Test TesterWorker initialization."""
        worker = TesterWorker(
            code_to_test="def test(): pass",
            model="gemini-2.5-flash",
            api_keys={"GEMINI_API_KEY": "test_key"},
            available_tools={},
            test_mode="all",
        )

        assert worker.code_to_test == "def test(): pass"
        assert worker.model == "gemini-2.5-flash"
        assert worker.test_mode == "all"
        assert worker.daemon is True
        assert isinstance(worker.result_queue, queue.Queue)
        assert isinstance(worker.status_queue, queue.Queue)

    def test_initialization_with_file_path(self):
        """Test TesterWorker initialization with file path."""
        worker = TesterWorker(
            code_to_test="/path/to/file.py",
            model="gemini-2.5-flash",
            api_keys={},
            available_tools={},
            file_path="/path/to/file.py",
        )

        assert worker.file_path == "/path/to/file.py"

    def test_emit_status(self):
        """Test status emission with throttling."""
        status_queue = queue.Queue()
        worker = TesterWorker(
            code_to_test="test",
            model="test",
            api_keys={},
            available_tools={},
            status_queue=status_queue,
        )

        worker._emit_status("Test message")
        assert not status_queue.empty()

        message = status_queue.get()
        assert message["type"] == "chat_message"
        assert message["sender"] == "tester"
        assert message["content"] == "Test message"

    def test_emit_status_throttling(self):
        """Test status emission throttling."""
        status_queue = queue.Queue()
        worker = TesterWorker(
            code_to_test="test",
            model="test",
            api_keys={},
            available_tools={},
            status_queue=status_queue,
        )

        # Emit multiple messages quickly
        worker._emit_status("Message 1")
        worker._emit_status("Message 2")
        worker._emit_status("Message 3")

        # Should only have one message due to throttling
        assert status_queue.qsize() == 1

    @patch("builtins.open", create=True)
    def test_load_code_if_file(self, mock_open):
        """Test loading code from file."""
        mock_open.return_value.__enter__.return_value.read.return_value = "file content"

        worker = TesterWorker(
            code_to_test="/path/to/file.py",
            model="test",
            api_keys={},
            available_tools={},
        )

        with patch("os.path.isfile", return_value=True):
            code = worker._load_code_if_file()
            assert code == "file content"

    def test_load_code_if_file_not_file(self):
        """Test loading code when not a file."""
        worker = TesterWorker(
            code_to_test="direct code content",
            model="test",
            api_keys={},
            available_tools={},
        )

        with patch("os.path.isfile", return_value=False):
            code = worker._load_code_if_file()
            assert code == "direct code content"

    def test_extract_tests(self):
        """Test extracting test code blocks from analysis."""
        worker = TesterWorker(
            code_to_test="test",
            model="test",
            api_keys={},
            available_tools={},
        )

        analysis = """
        Some text
        ```python
        def test_example():
            assert True
        ```
        More text
        """

        tests = worker._extract_tests(analysis)
        assert len(tests) == 1
        assert "def test_example" in tests[0]

    def test_extract_tests_multiple(self):
        """Test extracting multiple test code blocks."""
        worker = TesterWorker(
            code_to_test="test",
            model="test",
            api_keys={},
            available_tools={},
        )

        analysis = """
        ```python
        def test_one():
            pass
        ```
        ```python
        def test_two():
            pass
        ```
        """

        tests = worker._extract_tests(analysis)
        assert len(tests) == 2

    def test_extract_tests_no_tests(self):
        """Test extracting when no tests found."""
        worker = TesterWorker(
            code_to_test="test",
            model="test",
            api_keys={},
            available_tools={},
        )

        analysis = "No code blocks here"
        tests = worker._extract_tests(analysis)
        assert len(tests) == 0

    def test_get_result_timeout(self):
        """Test getting result with timeout."""
        worker = TesterWorker(
            code_to_test="test",
            model="test",
            api_keys={},
            available_tools={},
        )

        result = worker.get_result(timeout=0.1)
        assert result["status"] == "timeout"
        assert result["error_code"] == "worker_wait_timeout"

    def test_get_result_success(self):
        """Test getting result when available."""
        worker = TesterWorker(
            code_to_test="test",
            model="test",
            api_keys={},
            available_tools={},
        )

        worker.result_queue.put({"status": "completed", "result": "test"})
        result = worker.get_result(timeout=1.0)
        assert result["status"] == "completed"
        assert result["result"] == "test"

    def test_run_short_code_check(self):
        """Test that short code is detected correctly."""
        status_queue = queue.Queue()
        worker = TesterWorker(
            code_to_test="short",
            model="test",
            api_keys={},
            available_tools={},
            status_queue=status_queue,
        )

        # Test the code loading logic directly
        code = worker._load_code_if_file()
        assert len(code.strip()) < 10  # Code is too short

    def test_run_adversarial_validation_exists(self):
        """Test that run_adversarial_validation function exists."""
        assert callable(run_adversarial_validation)
