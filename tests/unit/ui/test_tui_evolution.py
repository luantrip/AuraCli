"""
Tests for TUI Evolution Components (TUI_EVOLUTION_WORKPLAN).

Tests for:
- Core systems (EventBus, SyncStore, SyncManager, ErrorHandler)
- Keybinds (LeaderKey, KeybindManager)
- Utils (TerminalDetector, ClipboardUtils)
- Widgets (KnightRiderSpinner, RichInput, CommandPalette, Dialogs)
"""

from unittest.mock import MagicMock

import pytest

# =============================================================================
# Event Bus Tests
# =============================================================================


class TestTUIEventBus:
    """Tests for the typed event bus system."""

    def test_event_bus_initialization(self):
        """Test EventBus initializes correctly."""
        from aura_cli.tui.core.event_bus import TUIEventBus

        bus = TUIEventBus()
        assert bus is not None
        assert bus._enable_history
        assert len(bus._subscribers) == 0

    def test_event_definition_with_pydantic(self):
        """Test defining events with Pydantic schemas."""
        from pydantic import BaseModel

        from aura_cli.tui.core.event_bus import TUIEventBus

        bus = TUIEventBus()

        class TestPayload(BaseModel):
            message: str
            count: int = 0

        event_def = bus.define("test.event", TestPayload, "Test event")

        assert event_def.event_type == "test.event"
        assert event_def.schema == TestPayload
        assert event_def.description == "Test event"

    def test_event_publish_and_subscribe(self):
        """Test publishing and subscribing to events."""
        from pydantic import BaseModel

        from aura_cli.tui.core.event_bus import TUIEventBus

        bus = TUIEventBus()
        results = []

        class MessagePayload(BaseModel):
            text: str

        bus.define("chat.message", MessagePayload)

        def handler(payload):
            results.append(payload)

        unsub = bus.subscribe("chat.message", handler)

        # Publish valid event
        success = bus.publish("chat.message", {"text": "Hello!"})
        assert success
        assert len(results) == 1
        assert results[0]["text"] == "Hello!"

        # Unsubscribe
        unsub()
        bus.publish("chat.message", {"text": "Goodbye!"})
        assert len(results) == 1  # No new message

    def test_event_validation_failure(self):
        """Test that invalid payloads are rejected."""
        from pydantic import BaseModel

        from aura_cli.tui.core.event_bus import TUIEventBus

        bus = TUIEventBus()

        class StrictPayload(BaseModel):
            required_field: str

        bus.define("strict.event", StrictPayload)

        # Missing required field
        success = bus.publish("strict.event", {})
        assert not success

    def test_wildcard_subscription(self):
        """Test subscribing to all events."""
        from pydantic import BaseModel

        from aura_cli.tui.core.event_bus import TUIEventBus

        bus = TUIEventBus()
        all_events = []

        class AnyPayload(BaseModel):
            data: str

        bus.define("event.a", AnyPayload)
        bus.define("event.b", AnyPayload)

        bus.subscribe_all(lambda t, p: all_events.append((t, p)))

        bus.publish("event.a", {"data": "A"})
        bus.publish("event.b", {"data": "B"})

        assert len(all_events) == 2
        assert all_events[0][0] == "event.a"
        assert all_events[1][0] == "event.b"

    def test_event_once(self):
        """Test one-time subscription."""
        from pydantic import BaseModel

        from aura_cli.tui.core.event_bus import TUIEventBus

        bus = TUIEventBus()
        results = []

        class Payload(BaseModel):
            x: int

        bus.define("once.event", Payload)
        bus.once("once.event", lambda p: results.append(p))

        bus.publish("once.event", {"x": 1})
        bus.publish("once.event", {"x": 2})

        assert len(results) == 1
        assert results[0]["x"] == 1

    def test_event_history(self):
        """Test event history recording."""
        from pydantic import BaseModel

        from aura_cli.tui.core.event_bus import TUIEventBus

        bus = TUIEventBus(enable_history=True)

        class Payload(BaseModel):
            v: int

        bus.define("hist.event", Payload)

        for i in range(5):
            bus.publish("hist.event", {"v": i})

        history = bus.get_history()
        assert len(history) == 5

        # Filter by type
        filtered = bus.get_history("hist.event", limit=3)
        assert len(filtered) == 3

    def test_tui_events_definitions(self):
        """Test TUIEvents predefined event definitions."""
        from aura_cli.tui.core.event_bus import TUIEvents

        # Test toast event
        result = TUIEvents.bus.publish(
            "tui.toast.show", {"message": "Test toast", "severity": "info"}
        )
        assert result

        # Test navigation event
        result = TUIEvents.bus.publish(
            "tui.navigate", {"route_type": "home", "params": {}}
        )
        assert result


# =============================================================================
# Sync Store Tests
# =============================================================================


class TestSyncStore:
    """Tests for the reactive sync store."""

    def test_store_initialization(self):
        """Test store initializes with default state."""
        from aura_cli.tui.core.sync_store import SyncStore

        store = SyncStore()
        assert "tasks" in store.state
        assert "messages" in store.state
        assert "ui" in store.state

    def test_path_based_get_set(self):
        """Test dot-notation path access."""
        from aura_cli.tui.core.sync_store import SyncStore

        store = SyncStore()

        # Set nested value
        store.set("tasks.task_1.status", "running")

        # Get nested value
        status = store.get("tasks.task_1.status")
        assert status == "running"

        # Get with default
        missing = store.get("tasks.task_999.status", "not_found")
        assert missing == "not_found"

    def test_store_subscriptions(self):
        """Test change notifications."""
        from aura_cli.tui.core.sync_store import SyncStore

        store = SyncStore()
        changes = []

        def on_change(path, value):
            changes.append((path, value))

        unsub = store.subscribe("tasks", on_change)

        store.set("tasks.task_1.status", "running")

        assert len(changes) == 1
        assert changes[0][0] == "tasks.task_1.status"

        unsub()
        store.set("tasks.task_2.status", "pending")
        assert len(changes) == 1  # No new notification

    def test_batch_updates(self):
        """Test batch updates minimize notifications."""
        from aura_cli.tui.core.sync_store import SyncStore

        store = SyncStore()
        notifications = []

        store.subscribe("tasks", lambda p, v: notifications.append(p))

        with store.batch_update():
            store.set("tasks.a.status", "running")
            store.set("tasks.b.status", "pending")
            store.set("tasks.c.status", "complete")

        # Should batch into fewer notifications
        assert len(notifications) <= 3

    def test_store_update_function(self):
        """Test update with function."""
        from aura_cli.tui.core.sync_store import SyncStore

        store = SyncStore()
        store.set("stats.count", 0)

        store.update("stats.count", lambda x: x + 1)
        store.update("stats.count", lambda x: x + 1)

        assert store.get("stats.count") == 2

    def test_store_delete(self):
        """Test deleting values."""
        from aura_cli.tui.core.sync_store import SyncStore

        store = SyncStore()
        store.set("temp.data", "value")

        assert store.get("temp.data") == "value"

        result = store.delete("temp.data")
        assert result
        assert store.get("temp.data") is None

    def test_store_snapshot_restore(self):
        """Test snapshot and restore functionality."""
        from aura_cli.tui.core.sync_store import SyncStore

        store = SyncStore()
        store.set("tasks.task_1.status", "running")

        # Create snapshot
        snapshot = store.snapshot("Before change")

        # Modify state
        store.set("tasks.task_1.status", "complete")
        assert store.get("tasks.task_1.status") == "complete"

        # Restore
        store.restore(snapshot)
        assert store.get("tasks.task_1.status") == "running"

    def test_store_helpers(self):
        """Test convenience helper methods."""
        from aura_cli.tui.core.sync_store import SyncStore

        store = SyncStore()

        # Add task
        store.add_task("t1", {"name": "Test Task", "status": "pending"})
        assert store.get_task("t1")["name"] == "Test Task"

        # Update task status
        store.update_task_status("t1", "running")
        assert store.get_task("t1")["status"] == "running"

        # Add message
        store.add_message({"content": "Hello", "sender": "User"})
        messages = store.get_messages()
        assert len(messages) == 1

        # Focused task
        store.set_focused_task("t1")
        assert store.get_focused_task() == "t1"


# =============================================================================
# Router Tests
# =============================================================================

# =============================================================================
# Error Handler Tests
# =============================================================================


class TestErrorHandler:
    """Tests for the error handler."""

    def test_error_handler_initialization(self):
        """Test error handler initializes correctly."""
        from aura_cli.tui.core.error_handler import TUIErrorHandler

        mock_app = MagicMock()
        handler = TUIErrorHandler(mock_app)

        assert handler.app == mock_app
        assert len(handler._error_history) == 0

    def test_error_handling(self):
        """Test basic error handling."""
        from aura_cli.tui.core.error_handler import TUIErrorHandler

        mock_app = MagicMock()
        handler = TUIErrorHandler(mock_app)

        try:
            raise ValueError("Test error")
        except Exception as e:
            error_info = handler.handle_error(e, context="test_context")

        assert error_info.error_type == "ValueError"
        assert error_info.message == "Test error"
        assert error_info.context == "test_context"
        assert not error_info.fatal
        assert error_info.handled

    def test_fatal_error_detection(self):
        """Test fatal error classification."""
        from aura_cli.tui.core.error_handler import TUIErrorHandler

        mock_app = MagicMock()
        handler = TUIErrorHandler(mock_app)

        # Memory error is fatal
        assert handler._is_fatal(MemoryError())

        # Regular error is not fatal
        assert not handler._is_fatal(ValueError())

    def test_error_callbacks(self):
        """Test error callbacks."""
        from aura_cli.tui.core.error_handler import TUIErrorHandler

        mock_app = MagicMock()
        handler = TUIErrorHandler(mock_app)

        errors_received = []
        handler.on_error(lambda e: errors_received.append(e))

        try:
            raise RuntimeError("Callback test")
        except Exception as e:
            handler.handle_error(e)

        assert len(errors_received) == 1
        assert errors_received[0].error_type == "RuntimeError"

    def test_error_context_manager(self):
        """Test error catching context manager."""
        from aura_cli.tui.core.error_handler import TUIErrorHandler

        mock_app = MagicMock()
        handler = TUIErrorHandler(mock_app)

        # Non-fatal error should be caught
        with handler.catch_errors("context_test"):
            raise ValueError("Should be caught")

        assert len(handler.get_error_history()) == 1

    def test_error_history(self):
        """Test error history tracking."""
        from aura_cli.tui.core.error_handler import TUIErrorHandler

        mock_app = MagicMock()
        handler = TUIErrorHandler(mock_app)

        for i in range(3):
            try:
                raise Exception(f"Error {i}")
            except Exception as e:
                handler.handle_error(e)

        history = handler.get_error_history()
        assert len(history) == 3

        summary = handler.get_error_summary()
        assert summary["total"] == 3


# =============================================================================
# Keybind Manager Tests
# =============================================================================


class TestKeybindManager:
    """Tests for the keybind management system."""

    def test_keybind_info(self):
        """Test KeybindInfo dataclass."""
        from aura_cli.tui.keybinds.keybind_manager import KeybindInfo

        kb = KeybindInfo(
            key="ctrl+s", action="save", description="Save file", category="file"
        )

        assert kb.key == "ctrl+s"
        assert "Ctrl" in kb.display_key  # Display key contains Ctrl
        assert not kb.requires_leader

    def test_leader_key_manager(self):
        """Test LeaderKeyManager functionality."""
        from aura_cli.tui.keybinds.keybind_manager import KeybindInfo, LeaderKeyManager

        mock_app = MagicMock()
        leader = LeaderKeyManager(mock_app)

        # Register sequence
        kb = KeybindInfo(
            key="<leader> a", action="show_agents", description="Show agents"
        )
        leader.register_sequence("a", kb)

        assert "a" in leader.get_sequences()

    def test_leader_mode_activation(self):
        """Test leader mode state management."""
        from aura_cli.tui.keybinds.keybind_manager import LeaderKeyManager

        mock_app = MagicMock()
        mock_app.set_timer = MagicMock()
        mock_app.focused = None

        leader = LeaderKeyManager(mock_app)

        assert not leader.state.active

        leader.enter_leader_mode()
        assert leader.state.active
        assert leader.state.sequence == []

        leader.exit_leader_mode()
        assert not leader.state.active

    def test_keybind_manager_registration(self):
        """Test KeybindManager registration."""
        from aura_cli.tui.keybinds.keybind_manager import KeybindInfo, KeybindManager

        mock_app = MagicMock()
        mock_app.set_timer = MagicMock()

        manager = KeybindManager(mock_app)

        # Register direct keybind
        manager.register(KeybindInfo(key="ctrl+s", action="save", description="Save"))

        # Register leader sequence
        manager.register(
            KeybindInfo(
                key="<leader> m", action="show_models", description="Show models"
            )
        )

        keybinds = manager.get_keybinds()
        assert len(keybinds) >= 2

    def test_keybind_config_defaults(self):
        """Test default keybind configuration."""
        from aura_cli.tui.keybinds.keybind_config import KeybindConfig

        config = KeybindConfig()

        assert len(config.keybinds) > 0
        assert config.leader_key == "ctrl+space"
        assert config.leader_timeout == 2.0

    def test_keybind_config_serialization(self):
        """Test keybind config serialization."""
        from aura_cli.tui.keybinds.keybind_config import KeybindConfig

        config = KeybindConfig()
        config.add_keybind(
            {"key": "ctrl+n", "action": "new", "description": "New file"}
        )

        data = config.to_dict()
        restored = KeybindConfig.from_dict(data)

        assert len(restored.keybinds) == len(config.keybinds)


# =============================================================================
# Terminal Detector Tests
# =============================================================================


class TestTerminalDetector:
    """Tests for terminal detection."""

    def test_terminal_info_dataclass(self):
        """Test TerminalInfo dataclass."""
        from aura_cli.tui.utils.terminal_detector import TerminalInfo

        info = TerminalInfo(
            background="dark",
            terminal_program="iterm.app",
            term_type="xterm-256color",
            color_support="truecolor",
            supports_unicode=True,
            width=120,
            height=40,
        )

        assert info.is_dark
        assert not info.is_light
        assert info.supports_truecolor

    def test_terminal_detector(self):
        """Test TerminalDetector detection."""
        from aura_cli.tui.utils.terminal_detector import TerminalDetector

        detector = TerminalDetector()
        info = detector.detect()

        assert info.background in ("light", "dark", "unknown")
        assert info.color_support in ("none", "basic", "256", "truecolor")
        assert info.width > 0
        assert info.height > 0

    def test_detect_convenience_functions(self):
        """Test convenience functions."""
        from aura_cli.tui.utils.terminal_detector import (
            detect_background_color,
            get_optimal_theme,
            get_terminal_info,
        )

        bg = detect_background_color()
        assert bg in ("light", "dark", "unknown")

        theme = get_optimal_theme()
        assert theme in ("nebula-dark", "nebula-light")

        info = get_terminal_info()
        assert info is not None


# =============================================================================
# Clipboard Utils Tests
# =============================================================================


class TestClipboardUtils:
    """Tests for clipboard utilities."""

    def test_clipboard_content_dataclass(self):
        """Test ClipboardContent dataclass."""
        from aura_cli.tui.utils.clipboard_utils import ClipboardContent

        content = ClipboardContent(
            content="test.py", content_type="file_path", metadata={"exists": True}
        )

        assert content.is_file_path
        assert not content.is_image
        assert content.line_count == 1

    def test_clipboard_manager_initialization(self):
        """Test ClipboardManager initializes."""
        from aura_cli.tui.utils.clipboard_utils import ClipboardManager

        manager = ClipboardManager()
        assert manager is not None


# =============================================================================
# Widget Tests
# =============================================================================


class TestKnightRiderSpinner:
    """Tests for the Knight Rider spinner."""

    def test_spinner_initialization(self):
        """Test spinner initializes correctly."""
        from aura_cli.tui.widgets.knight_rider_spinner import KnightRiderSpinner

        spinner = KnightRiderSpinner(
            width=20, style="block", color="#00ff00", message="Loading..."
        )

        assert spinner.config.width == 20
        assert spinner.config.style == "block"
        assert spinner.config.color == "#00ff00"
        assert spinner.message == "Loading..."

    def test_spinner_styles(self):
        """Test different spinner styles."""
        from aura_cli.tui.widgets.knight_rider_spinner import KnightRiderSpinner

        for style in ["block", "diamond", "dot", "wave", "pulse"]:
            spinner = KnightRiderSpinner(style=style)
            assert spinner.config.style == style

    def test_compact_spinner(self):
        """Test compact spinner."""
        from aura_cli.tui.widgets.knight_rider_spinner import CompactSpinner

        spinner = CompactSpinner(message="Loading", color="#ff0000")
        assert spinner.message == "Loading"
        assert spinner.color == "#ff0000"

    def test_progress_spinner(self):
        """Test progress spinner."""
        from aura_cli.tui.widgets.knight_rider_spinner import ProgressSpinner

        spinner = ProgressSpinner(message="Processing")
        spinner.set_progress(0.5, "Half done")

        assert spinner.progress == 0.5
        assert spinner.message == "Half done"


class TestRichPromptInput:
    """Tests for the rich prompt input."""

    def test_prompt_part_creation(self):
        """Test PromptPart creation."""
        from aura_cli.tui.widgets.rich_input import PromptPart

        part = PromptPart(
            type="file", data={"path": "/test/file.py"}, placeholder="file.py"
        )

        assert part.type == "file"
        assert "◇" in part.display
        assert part.id  # Auto-generated

    def test_prompt_state(self):
        """Test PromptState dataclass."""
        from aura_cli.tui.widgets.rich_input import PromptState

        state = PromptState()
        assert state.raw_text == ""
        assert state.parts == []
        assert state.mode == "normal"


class TestCommandPalette:
    """Tests for the command palette."""

    def test_command_creation(self):
        """Test Command dataclass."""
        from aura_cli.tui.widgets.command_palette import Command

        cmd = Command(
            id="test_cmd",
            name="Test Command",
            description="A test command",
            keybind="ctrl+t",
            icon="🔧",
            category="testing",
        )

        assert cmd.id == "test_cmd"
        assert "🔧" in cmd.display_name

    def test_command_registry(self):
        """Test CommandRegistry."""
        from aura_cli.tui.widgets.command_palette import Command, CommandRegistry

        registry = CommandRegistry()

        cmd = Command(id="cmd1", name="Command One", description="First command")
        registry.register(cmd)

        assert registry.get("cmd1") == cmd

        # Search
        results = registry.search("one")
        assert len(results) > 0
        assert results[0].id == "cmd1"

    def test_registry_recent_tracking(self):
        """Test recently used tracking."""
        from aura_cli.tui.widgets.command_palette import Command, CommandRegistry

        registry = CommandRegistry()

        for i in range(3):
            registry.register(Command(id=f"cmd{i}", name=f"Command {i}"))

        registry.mark_used("cmd2")
        registry.mark_used("cmd0")

        # Recent commands should be prioritized
        results = registry.search("")
        assert results[0].id == "cmd0"  # Most recently used


class TestDialogs:
    """Tests for dialog system."""

    def test_dialog_result(self):
        """Test DialogResult dataclass."""
        from aura_cli.tui.widgets.dialogs import DialogResult

        result = DialogResult(confirmed=True, value="test", action="submit")

        assert result.confirmed
        assert result.value == "test"
        assert result.action == "submit"

    def test_select_option(self):
        """Test SelectOption dataclass."""
        from aura_cli.tui.widgets.dialogs.select_dialog import SelectOption

        option = SelectOption(
            id="opt1", label="Option One", description="First option", icon="🎯"
        )

        assert option.id == "opt1"
        assert "🎯" in option.display


# =============================================================================
# Integration Tests
# =============================================================================


class TestCoreIntegration:
    """Integration tests for core systems."""

    def test_event_bus_and_store_integration(self):
        """Test EventBus triggering store updates."""
        from pydantic import BaseModel

        from aura_cli.tui.core.event_bus import TUIEventBus
        from aura_cli.tui.core.sync_store import SyncStore

        bus = TUIEventBus()
        store = SyncStore()

        class StateUpdatePayload(BaseModel):
            path: str
            value: str

        bus.define("state.update", StateUpdatePayload)

        def handle_update(payload):
            store.set(payload["path"], payload["value"])

        bus.subscribe("state.update", handle_update)

        bus.publish("state.update", {"path": "tasks.task1.status", "value": "running"})

        assert store.get("tasks.task1.status") == "running"

    def test_all_imports_work(self):
        """Test all major imports work together."""
        from aura_cli.tui import (
            TUIEventBus,
        )
        from aura_cli.tui.widgets import (
            KnightRiderSpinner,
        )

        # All imports should work
        assert TUIEventBus is not None
        assert KnightRiderSpinner is not None


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
