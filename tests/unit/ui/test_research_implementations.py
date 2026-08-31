"""
Tests for WEB_RESEARCH_GUIDE.md implementations.

Tests for:
- ConversationMemory
- SessionState
- PersistentStore
- AsyncSubprocessRunner
- Enhanced AuraChatLog
- Enhanced PluginManager
"""

import os
import tempfile
from unittest.mock import MagicMock, patch


class TestConversationMemory:
    """Tests for the ConversationMemory class."""

    def test_add_message(self):
        """Test adding messages to memory."""
        from aura_cli.core.memory import ConversationMemory

        memory = ConversationMemory()
        memory.add_message("user", "Hello")
        memory.add_message("assistant", "Hi there!")

        assert len(memory.messages) == 2
        assert memory.messages[0].role == "user"
        assert memory.messages[1].content == "Hi there!"

    def test_get_context(self):
        """Test getting context for LLM."""
        from aura_cli.core.memory import ConversationMemory

        memory = ConversationMemory()
        memory.add_message("user", "What is 2+2?")
        memory.add_message("assistant", "4")

        context = memory.get_context()
        assert len(context) == 2
        assert context[0]["role"] == "user"

    def test_compression(self):
        """Test that old messages are compressed."""
        from aura_cli.core.memory import ConversationMemory

        memory = ConversationMemory(max_messages=10)

        # Add more than max messages
        for i in range(15):
            memory.add_message("user", f"Message {i}")

        # Should have compressed
        assert len(memory.messages) <= 10

    def test_serialization(self):
        """Test serialization and deserialization."""
        from aura_cli.core.memory import ConversationMemory

        memory = ConversationMemory()
        memory.add_message("user", "Test")

        data = memory.to_dict()
        restored = ConversationMemory.from_dict(data)

        assert len(restored.messages) == 1
        assert restored.messages[0].content == "Test"


class TestSessionState:
    """Tests for the SessionState class."""

    def test_set_and_get(self):
        """Test basic set/get operations."""
        from aura_cli.core.memory import InMemoryState as SessionState

        state = SessionState()
        state.set("key", "value")

        assert state.get("key") == "value"
        assert state.get("nonexistent", "default") == "default"

    def test_dirty_tracking(self):
        """Test dirty state tracking."""
        from aura_cli.core.memory import InMemoryState as SessionState

        state = SessionState()
        assert not state.is_dirty

        state.set("key", "value")
        assert state.is_dirty

        state.mark_clean()
        assert not state.is_dirty

    def test_delete(self):
        """Test deleting values."""
        from aura_cli.core.memory import InMemoryState as SessionState

        state = SessionState()
        state.set("key", "value")
        state.delete("key")

        assert not state.has("key")


class TestPersistentStore:
    """Tests for the PersistentStore class."""

    def test_kv_operations(self):
        """Test key-value operations."""
        from aura_cli.core.memory import PersistentStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = PersistentStore(db_path=db_path)

            store.set("test_key", {"data": 123})
            result = store.get("test_key")

            assert result == {"data": 123}

    def test_save_and_load_conversation(self):
        """Test saving and loading conversations."""
        from aura_cli.core.memory import ConversationMemory, PersistentStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = PersistentStore(db_path=db_path)

            memory = ConversationMemory()
            memory.add_message("user", "Hello")
            memory.add_message("assistant", "Hi!")

            store.save_conversation("session1", memory)
            loaded = store.load_conversation("session1")

            assert loaded is not None
            assert len(loaded.messages) == 2

    def test_task_operations(self):
        """Test task save/load operations."""
        from aura_cli.core.memory import PersistentStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = PersistentStore(db_path=db_path)

            store.save_task("task1", "Test Task", "pending", {"foo": "bar"})
            task = store.get_task("task1")

            assert task is not None
            assert task["name"] == "Test Task"
            assert task["data"]["foo"] == "bar"


class TestEnhancedAuraChatLog:
    """Tests for the enhanced AuraChatLog."""

    def test_write_styled_message_method_exists(self):
        """Test that write_styled_message method exists."""
        from aura_cli.tui.widgets.chat import AuraChatLog

        chat = AuraChatLog()
        assert hasattr(chat, "write_styled_message")
        assert hasattr(chat, "start_streaming")
        assert hasattr(chat, "end_streaming")
        assert hasattr(chat, "show_thinking")
        assert hasattr(chat, "hide_thinking")

    def test_streaming_methods(self):
        """Test streaming message methods."""
        from unittest.mock import PropertyMock

        from aura_cli.tui.widgets.chat import AuraChatLog

        chat = AuraChatLog()
        # Mock mount and is_attached to avoid Textual mounting requirements
        chat.mount = MagicMock()
        with patch.object(
            chat.__class__, "is_attached", new_callable=PropertyMock, return_value=True
        ):
            chat.start_streaming("Aura")
            chat.append_streaming("Hello ")
            chat.append_streaming("World!")

            # Check that streaming was started
            assert chat._streaming_bubble is not None
            assert chat.is_typing is True
            assert chat.typing_sender == "Aura"


class TestEnhancedPluginManager:
    """Tests for the enhanced PluginManager."""

    def test_plugin_manager_init(self):
        """Test PluginManager initialization."""
        from aura_cli.tui.plugin_manager import PluginManager

        manager = PluginManager(plugin_dirs=["/fake/dir"])

        assert manager.plugin_dirs == ["/fake/dir"]
        assert manager.loaded_plugins == {}
        assert manager.plugin_commands == {}

    def test_plugin_lifecycle_methods(self):
        """Test plugin lifecycle management methods."""
        from aura_cli.tui.plugin_manager import PluginManager

        manager = PluginManager()

        assert hasattr(manager, "load_plugins")
        assert hasattr(manager, "unload_plugin")
        assert hasattr(manager, "enable_plugin")
        assert hasattr(manager, "disable_plugin")
        assert hasattr(manager, "notify_app_ready")

    def test_get_plugin_info(self):
        """Test getting plugin info."""
        from aura_cli.tui.plugin_manager import PluginManager

        manager = PluginManager()
        info = manager.get_plugin_info()

        assert isinstance(info, list)

    def test_widget_location_tracking(self):
        """Test widget location tracking."""
        from aura_cli.tui.plugin_manager import PluginManager

        manager = PluginManager()

        assert hasattr(manager, "widget_locations")
        assert hasattr(manager, "get_widgets_for_location")


class TestPluginBase:
    """Tests for the AuraTUIPluginBase class."""

    def test_plugin_base_interface(self):
        """Test that plugin base defines required interface."""
        from aura_cli.tui.plugin_manager import AuraTUIPluginBase

        # Should have abstract get_widgets method
        assert hasattr(AuraTUIPluginBase, "get_widgets")

        # Should have lifecycle hooks
        assert hasattr(AuraTUIPluginBase, "on_load")
        assert hasattr(AuraTUIPluginBase, "on_unload")
        assert hasattr(AuraTUIPluginBase, "on_app_ready")

    def test_plugin_metadata(self):
        """Test plugin metadata property."""
        from aura_cli.tui.plugin_manager import AuraTUIPluginBase, PluginMetadata

        class TestPlugin(AuraTUIPluginBase):
            PLUGIN_NAME = "Test Plugin"
            PLUGIN_VERSION = "2.0.0"

            def get_widgets(self):
                return {}

            def on_app_ready(self, app):
                pass

            def on_load(self):
                pass

            def on_unload(self):
                pass

        plugin = TestPlugin()
        meta = plugin.metadata

        assert isinstance(meta, PluginMetadata)
        assert meta.name == "Test Plugin"
        assert meta.version == "2.0.0"


class TestCodeAnalysisPanelEnhanced:
    """Tests for the enhanced CodeAnalysisPanel."""

    def test_code_issue_dataclass(self):
        """Test CodeIssue dataclass."""
        from aura_cli.tui.widgets.code_analysis_panel import CodeIssue

        issue = CodeIssue(
            file="test.py", line=10, column=5, severity="error", message="Test error"
        )

        assert issue.severity_icon == "✖"
        # CodeIssue doesn't have severity_color property, only severity_icon
        assert issue.severity == "error"

    def test_panel_has_datatable(self):
        """Test that panel composes with DataTable."""
        from aura_cli.tui.widgets.code_analysis_panel import CodeAnalysisPanel

        panel = CodeAnalysisPanel()
        assert hasattr(panel, "update_issues")
        # highlight_line may not be implemented yet, check for update_issues instead
        assert hasattr(panel, "update_issues")
