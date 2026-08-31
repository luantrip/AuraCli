"""Tests for core/stats.py — StatsTracker."""

import pytest

from aura_cli.core.stats import StatsTracker, get_stats, reset_stats


@pytest.fixture(autouse=True)
def reset():
    reset_stats()
    yield
    reset_stats()


class TestStatsTracker:
    def test_initial_state(self):
        s = StatsTracker()
        assert s.tokens_used == 0
        assert s.files_edited == 0
        assert s.files_read == 0
        assert s.current_status == "idle"
        assert s.skip_confirmations is False

    def test_add_tokens(self):
        s = StatsTracker()
        s.add_tokens(
            {"total_tokens": 100, "prompt_tokens": 60, "completion_tokens": 40}
        )
        assert s.tokens_used == 100
        assert s.prompt_tokens == 60
        assert s.completion_tokens == 40

    def test_add_tokens_accumulates(self):
        s = StatsTracker()
        s.add_tokens({"total_tokens": 50})
        s.add_tokens({"total_tokens": 30})
        assert s.tokens_used == 80

    def test_increment_files_edited(self):
        s = StatsTracker()
        s.increment_files_edited("main.py")
        s.increment_files_edited("utils.py")
        assert s.files_edited == 2

    def test_increment_files_read(self):
        s = StatsTracker()
        s.increment_files_read("readme.md")
        assert s.files_read == 1

    def test_increment_files_created(self):
        s = StatsTracker()
        s.increment_files_created("new.py")
        assert s.files_created == 1

    def test_set_status(self):
        s = StatsTracker()
        s.set_status("thinking", "Processing...")
        assert s.current_status == "thinking"
        assert s.status_message == "Processing..."

    def test_set_model(self):
        s = StatsTracker()
        s.set_model("gemini/gemini-2.5-flash")
        assert s.current_model == "gemini/gemini-2.5-flash"

    def test_track_tool_usage(self):
        s = StatsTracker()
        s.track_tool_usage("read_file")
        s.track_tool_usage("read_file")
        s.track_tool_usage("write_file")
        assert s.tools_used["read_file"] == 2
        assert s.tools_used["write_file"] == 1

    def test_set_notification(self):
        s = StatsTracker()
        s.set_notification("Test notification", duration_seconds=5.0)
        assert s.notification_message == "Test notification"
        assert s.notification_expires_at is not None

    def test_get_stats_snapshot(self):
        s = StatsTracker()
        s.add_tokens({"total_tokens": 200})
        # get_stats_snapshot is a module-level function, not instance method
        from aura_cli.core.stats import get_stats_snapshot

        snap = get_stats_snapshot()
        assert isinstance(snap, dict)

    def test_add_shell_command(self):
        s = StatsTracker()
        s.add_shell_command("ls -la", 0.5)
        assert s.shell_commands_run == 1
        assert s.shell_command_total_time == pytest.approx(0.5)


class TestGetStats:
    def test_returns_singleton(self):
        s1 = get_stats()
        s2 = get_stats()
        assert s1 is s2

    def test_reset_creates_new_instance(self):
        s1 = get_stats()
        s1.add_tokens({"total_tokens": 999})
        reset_stats()
        s2 = get_stats()
        assert s2.tokens_used == 0
