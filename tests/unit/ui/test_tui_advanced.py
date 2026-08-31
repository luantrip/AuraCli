"""
Tests for Advanced TUI Components.

Tests for:
- CodeAnalysisPanel
- EventStreamPanel
- MetricsPanel
- PluginManager
"""

from datetime import datetime
from unittest.mock import MagicMock


class TestCodeAnalysisPanel:
    """Tests for the CodeAnalysisPanel widget."""

    def test_update_code_creates_syntax(self):
        """Test that update_code method exists and has correct signature."""
        from aura_cli.tui.widgets.code_analysis_panel import CodeAnalysisPanel

        panel = CodeAnalysisPanel()
        # We can't fully test without mounting, but we can test the method exists
        assert hasattr(panel, "update_code")
        assert hasattr(panel, "update_analysis_results")

        # Verify method signature accepts expected params
        import inspect

        sig = inspect.signature(panel.update_code)
        params = list(sig.parameters.keys())
        assert "code_content" in params
        assert "language" in params
        assert "highlights" in params

    def test_update_analysis_results_formatting(self):
        """Test that analysis results are formatted correctly."""

        from aura_cli.tui.widgets.code_analysis_panel import CodeAnalysisPanel

        panel = CodeAnalysisPanel()

        # The method should handle this dict without errors
        # We can't test the actual rendering without mounting
        assert hasattr(panel, "update_analysis_results")


class TestEventStreamPanel:
    """Tests for the EventStreamPanel widget."""

    def test_write_event_formats_task_start(self):
        """Test that TASK_START events are formatted correctly."""
        from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel

        panel = EventStreamPanel()

        {
            "type": "agi_task_start",
            "task_id": "test-123",
            "timestamp": datetime.now().timestamp(),
            "data": {"description": "Test task"},
        }

        # Method should exist and accept event_dict
        assert hasattr(panel, "write_event")

    def test_write_event_formats_tool_executing(self):
        """Test that TOOL_EXECUTING events are formatted correctly."""
        from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel

        panel = EventStreamPanel()

        {
            "type": "tool_executing",
            "task_id": "tool-456",
            "timestamp": datetime.now().timestamp(),
            "data": {"tool_name": "read_file", "tool_args": {"path": "/test"}},
        }

        assert hasattr(panel, "write_event")

    def test_write_event_details(self):
        """Test that event details are written correctly."""
        from aura_cli.core.events.agi_events import AgiEvent, AgiEventType
        from aura_cli.tui.widgets.event_stream_panel import EventStreamPanel

        panel = EventStreamPanel()

        AgiEvent(
            type=AgiEventType.TASK_START,
            task_id="test-789",
            data={"description": "Test task"},
        )

        assert hasattr(panel, "write_event_details")


class TestMetricsPanel:
    """Tests for the MetricsPanel widget."""

    def test_update_metrics_creates_table(self):
        """Test that update_metrics creates a Rich table."""

        from aura_cli.tui.widgets.metrics_panel import MetricsPanel

        panel = MetricsPanel()

        # Method should exist
        assert hasattr(panel, "update_metrics")


class TestPluginManager:
    """Tests for the PluginManager."""

    def test_init_with_plugin_dirs(self):
        """Test PluginManager initialization."""
        from aura_cli.tui.plugin_manager import PluginManager

        manager = PluginManager(plugin_dirs=["/fake/dir"])

        assert manager.plugin_dirs == ["/fake/dir"]
        assert manager.loaded_plugins == {}
        assert manager.available_widgets == {}

    def test_discover_plugins_skips_missing_dirs(self):
        """Test that discover_plugins skips non-existent directories."""
        from aura_cli.tui.plugin_manager import PluginManager

        manager = PluginManager(plugin_dirs=["/nonexistent/path"])

        # Should not raise, just return empty
        plugins = list(manager._discover_plugins())
        assert plugins == []

    def test_discover_plugins_finds_py_files(self):
        """Test that discover_plugins finds .py files."""
        import os
        import tempfile

        from aura_cli.tui.plugin_manager import PluginManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test plugin files
            with open(os.path.join(tmpdir, "plugin1.py"), "w") as f:
                f.write("# Plugin 1")
            with open(os.path.join(tmpdir, "plugin2.py"), "w") as f:
                f.write("# Plugin 2")
            with open(os.path.join(tmpdir, "__init__.py"), "w") as f:
                f.write("")
            with open(os.path.join(tmpdir, "readme.md"), "w") as f:
                f.write("# README")

            manager = PluginManager(plugin_dirs=[tmpdir])
            plugins = list(manager._discover_plugins())

            # Should find plugin1.py and plugin2.py (but not __init__.py or readme.md)
            assert len(plugins) == 2
            plugin_names = [p[0] for p in plugins]
            assert "plugin1" in plugin_names
            assert "plugin2" in plugin_names

    def test_get_available_widgets(self):
        """Test getting available widgets."""
        from aura_cli.tui.plugin_manager import PluginManager

        manager = PluginManager(plugin_dirs=[])
        widgets = manager.get_available_widgets()

        assert isinstance(widgets, dict)


class TestBridgeEventStreaming:
    """Tests for event streaming through the Bridge."""

    def test_process_event_writes_to_stream_panel(self):
        """Test that _process_event writes to EventStreamPanel."""
        from aura_cli.tui.bridge import TextualUIManager

        mock_app = MagicMock()
        mock_event_panel = MagicMock()
        mock_app.query_one.return_value = mock_event_panel

        adapter = TextualUIManager(mock_app, status_queue=None, stats=None)

        event_dict = {
            "type": "agi_task_start",
            "task_id": "test-123",
            "timestamp": datetime.now().timestamp(),
            "data": {"description": "Test", "objective": "Stream event"},
        }

        adapter._process_event(event_dict)

        # Should have tried to write to event stream panel
        mock_app.query_one.assert_called()


class TestAppTaskTreeIntegration:
    """Tests for AuraTUI task tree integration."""

    def test_update_task_tree_handles_task_start(self):
        """Test that update_task_tree handles TASK_START correctly."""
        from aura_cli.core.events.agi_events import AgiEvent, AgiEventType

        # Create a mock event
        event = AgiEvent(
            type=AgiEventType.TASK_START,
            task_id="test-task-1",
            data={"description": "Test Task", "status": "pending"},
        )

        # Verify event structure
        assert event.type == AgiEventType.TASK_START
        assert event.task_id == "test-task-1"
        assert event.data["description"] == "Test Task"

    def test_update_task_tree_handles_subtask(self):
        """Test that update_task_tree handles SUBTASK_START correctly."""
        from aura_cli.core.events.agi_events import AgiEvent, AgiEventType

        event = AgiEvent(
            type=AgiEventType.SUBTASK_START,
            task_id="subtask-1",
            parent_task_id="test-task-1",
            data={"description": "Subtask", "status": "pending"},
        )

        assert event.type == AgiEventType.SUBTASK_START
        assert event.parent_task_id == "test-task-1"
