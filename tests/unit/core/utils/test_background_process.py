"""Unit tests for the background process supervisor using process fakes."""

from unittest.mock import MagicMock, patch

import pytest

from aura_cli.core.utils.background_process import BackgroundProcessSupervisor


class TestBackgroundProcessSupervisor:
    def test_start_registers_owner_and_process_evidence(self):
        process = MagicMock(pid=101)
        factory = MagicMock(return_value=process)
        supervisor = BackgroundProcessSupervisor(
            process_factory=factory, clock=lambda: 10.0
        )

        record = supervisor.start(
            ["fake-tool", "--once"], owner_task="task-1", cwd="/tmp"
        )

        assert record.pid == 101
        assert record.command == ("fake-tool", "--once")
        assert record.owner_task == "task-1"
        assert record.status == "running"
        assert record.started_at == 10.0
        assert factory.call_args.args[0] == ["fake-tool", "--once"]
        assert factory.call_args.kwargs == {
            "shell": False,
            "stdout": __import__("subprocess").DEVNULL,
            "stderr": __import__("subprocess").DEVNULL,
            "cwd": "/tmp",
            "start_new_session": True,
        }

    def test_refresh_transitions_finished_process(self):
        process = MagicMock(pid=102)
        process.poll.side_effect = [None, 0]
        clock_values = iter([20.0, 21.5])
        supervisor = BackgroundProcessSupervisor(
            process_factory=MagicMock(return_value=process),
            clock=lambda: next(clock_values),
        )
        supervisor.start(["fake-tool"])

        assert supervisor.snapshot()[0].status == "running"
        record = supervisor.get(102)

        assert record is not None
        assert record.status == "completed"
        assert record.exit_code == 0
        assert record.finished_at == 21.5

    @patch("aura_cli.core.utils.background_process.IS_WINDOWS", False)
    @patch("aura_cli.core.utils.background_process.os.getpgid", return_value=103)
    @patch("aura_cli.core.utils.background_process.os.killpg")
    def test_cancel_signals_group_and_reaps_handle(self, mock_killpg, _mock_getpgid):
        process = MagicMock(pid=103)
        process.poll.side_effect = [None, -15]
        supervisor = BackgroundProcessSupervisor(
            process_factory=MagicMock(return_value=process), clock=lambda: 30.0
        )
        supervisor.start(["fake-tool"])

        record = supervisor.cancel(103)

        assert record is not None
        assert record.status == "cancelled"
        assert record.exit_code == -15
        assert record.finished_at == 30.0
        mock_killpg.assert_called_once()
        process.wait.assert_called_once_with(timeout=1)

    @patch("aura_cli.core.utils.background_process.IS_WINDOWS", False)
    @patch("aura_cli.core.utils.background_process.os.getpgid", return_value=104)
    @patch("aura_cli.core.utils.background_process.os.killpg")
    def test_cancel_escalates_when_graceful_wait_times_out(
        self, mock_killpg, _mock_getpgid
    ):
        process = MagicMock(pid=104)
        process.poll.side_effect = [None, -9]
        process.wait.side_effect = [
            __import__("subprocess").TimeoutExpired(["fake-tool"], 1),
            None,
        ]
        supervisor = BackgroundProcessSupervisor(
            process_factory=MagicMock(return_value=process)
        )
        supervisor.start(["fake-tool"])

        record = supervisor.cancel(104)

        assert record is not None
        assert record.status == "cancelled"
        assert record.exit_code == -9
        assert mock_killpg.call_count == 2
        assert process.wait.call_count == 2

    def test_reap_removes_only_finished_records(self):
        running = MagicMock(pid=105)
        running.poll.return_value = None
        finished = MagicMock(pid=106)
        finished.poll.return_value = 2
        factory = MagicMock(side_effect=[running, finished])
        supervisor = BackgroundProcessSupervisor(
            process_factory=factory, clock=lambda: 40.0
        )
        supervisor.start(["running"])
        supervisor.start(["finished"])

        reaped = supervisor.reap()

        assert [record.pid for record in reaped] == [106]
        assert supervisor.get(105) is not None
        assert supervisor.get(106) is None

    def test_empty_command_is_rejected(self):
        supervisor = BackgroundProcessSupervisor(process_factory=MagicMock())

        with pytest.raises(ValueError, match="cannot be empty"):
            supervisor.start([])

    def test_unknown_pid_is_safe(self):
        supervisor = BackgroundProcessSupervisor(process_factory=MagicMock())

        assert supervisor.get(999) is None
        assert supervisor.cancel(999) is None
        assert supervisor.reap(999) == []
