"""Keybinding System for Aura TUI.

Comprehensive keybinding management with leader keys and persistence.

Components:
- KeybindManager: Main keybind registry and dispatcher
- KeybindInfo: Keybind metadata dataclass
- LeaderKeyManager: Multi-key sequence support (Vim-style)
- KeybindConfig: Configuration management
- KeybindPersistence: Save/load keybind profiles

Features:
- Leader key system for expandable keybindings
- Configurable keybind registry
- Multi-key sequence support
- Persistent configuration with profiles
- Default keybinds with merge support
"""

from aura_cli.tui.keybinds.keybind_config import (
    DEFAULT_KEYBINDS,
    KeybindConfig,
    KeybindPersistence,
    get_keybind_persistence,
    load_keybinds,
    merge_with_defaults,
    save_keybinds,
)
from aura_cli.tui.keybinds.keybind_manager import (
    KeybindInfo,
    KeybindManager,
    LeaderKeyManager,
)

__all__ = [
    "DEFAULT_KEYBINDS",
    "KeybindConfig",
    "KeybindInfo",
    "KeybindManager",
    "KeybindPersistence",
    "LeaderKeyManager",
    "get_keybind_persistence",
    "load_keybinds",
    "merge_with_defaults",
    "save_keybinds",
]
