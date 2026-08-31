"""Textual-based Terminal User Interface for Aura CLI.

Exports AuraTUI (main app), TextualUIManager (bridge adapter), EventBus,
SyncManager, SyncStore, ErrorHandler, KeybindManager, LeaderKeyManager,
ConversationMemory, PluginManager, AsyncSubprocessRunner and helpers.
Uses lazy imports to avoid circular dependencies.
"""

# Lazy imports to avoid circular dependencies
_LAZY_MAP = {
    "AuraTUI": "aura_cli.tui.app",
    "TextualUIManager": "aura_cli.tui.bridge",
    "TUIEventBus": "aura_cli.tui.core",
    "TUIEvents": "aura_cli.tui.core",
    "EventDefinition": "aura_cli.tui.core",
    "SyncManager": "aura_cli.tui.core",
    "SyncStore": "aura_cli.tui.core",
    "TUIErrorHandler": "aura_cli.tui.core",
    "get_error_handler": "aura_cli.tui.core.error_handler",
    "handle_error": "aura_cli.tui.core.error_handler",
    "set_error_handler": "aura_cli.tui.core.error_handler",
    "get_store": "aura_cli.tui.core.sync_store",
    "reset_store": "aura_cli.tui.core.sync_store",
    "KeybindManager": "aura_cli.tui.keybinds",
    "KeybindInfo": "aura_cli.tui.keybinds",
    "LeaderKeyManager": "aura_cli.tui.keybinds",
    "KeybindConfig": "aura_cli.tui.keybinds",
    "DEFAULT_KEYBINDS": "aura_cli.tui.keybinds",
    "load_keybinds": "aura_cli.tui.keybinds",
    "save_keybinds": "aura_cli.tui.keybinds",
    "KeybindPersistence": "aura_cli.tui.keybinds",
    "get_keybind_persistence": "aura_cli.tui.keybinds",
    "SessionState": "aura_cli.core.memory",
    "PersistentStore": "aura_cli.core.memory",
    "get_persistent_store": "aura_cli.core.memory",
    "PluginManager": "aura_cli.tui.plugin_manager",
    "AuraTUIPluginBase": "aura_cli.tui.plugin_manager",
    "AuraTUIPluginWidget": "aura_cli.tui.plugin_manager",
    "PluginMetadata": "aura_cli.tui.plugin_manager",
    "TerminalDetector": "aura_cli.tui.utils",
    "ClipboardManager": "aura_cli.tui.utils",
    "detect_background_color": "aura_cli.tui.utils",
    "get_clipboard": "aura_cli.tui.utils",
    "get_optimal_theme": "aura_cli.tui.utils",
    "get_terminal_info": "aura_cli.tui.utils",
    "set_clipboard": "aura_cli.tui.utils",
}


def __getattr__(name):
    """Lazy import attributes."""
    if name == "ConversationMemory":
        import threading

        if threading.current_thread() is threading.main_thread():
            from aura_cli.core.memory import ConversationMemory

            return ConversationMemory
        else:
            from pathlib import Path
            import tempfile

            from aura_cli.adk.memory import PersistentMemory

            memory_path = Path(tempfile.gettempdir()) / "aura_conversation_memory.jsonl"
            return lambda *args, **kwargs: PersistentMemory(memory_path)

    if name == "SessionState":
        # tui/memory re-exported InMemoryState as SessionState
        from aura_cli.core.memory import InMemoryState

        return InMemoryState

    if name in _LAZY_MAP:
        import importlib

        mod = importlib.import_module(_LAZY_MAP[name])
        return getattr(mod, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DEFAULT_KEYBINDS",
    "AuraTUI",
    "AuraTUIPluginBase",
    "AuraTUIPluginWidget",
    "ClipboardManager",
    "ConversationMemory",
    "EventDefinition",
    "KeybindConfig",
    "KeybindInfo",
    "KeybindManager",
    "KeybindPersistence",
    "LeaderKeyManager",
    "PersistentStore",
    "PluginManager",
    "PluginMetadata",
    "SessionState",
    "SyncManager",
    "SyncStore",
    "TUIErrorHandler",
    "TUIEventBus",
    "TUIEvents",
    "TerminalDetector",
    "TextualUIManager",
    "detect_background_color",
    "get_clipboard",
    "get_error_handler",
    "get_keybind_persistence",
    "get_optimal_theme",
    "get_persistent_store",
    "get_store",
    "get_terminal_info",
    "handle_error",
    "load_keybinds",
    "reset_store",
    "save_keybinds",
    "set_clipboard",
    "set_error_handler",
]
