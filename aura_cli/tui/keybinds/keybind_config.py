"""
Keybind Configuration for Aura TUI.

Provides default keybindings and configuration persistence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.tui.keybinds.keybind_manager import KeybindInfo

logger = logging.getLogger(__name__)


DEFAULT_KEYBINDS: List[Dict[str, Any]] = [
    {
        "key": "ctrl+c",
        "action": "quit",
        "description": "Quit application",
        "category": "navigation",
    },
    {
        "key": "ctrl+l",
        "action": "clear_chat",
        "description": "Clear chat",
        "category": "navigation",
    },
    {
        "key": "escape",
        "action": "cancel",
        "description": "Cancel / Close dialog",
        "category": "navigation",
    },
    {
        "key": "ctrl+e",
        "action": "toggle_panel",
        "description": "Toggle analysis/events panel",
        "category": "panels",
    },
    {
        "key": "ctrl+s",
        "action": "show_code_analysis",
        "description": "Show code analysis",
        "category": "panels",
    },
    {
        "key": "f",
        "action": "toggle_focus_mode",
        "description": "Toggle focus mode",
        "category": "panels",
    },
    {
        "key": "ctrl+p",
        "action": "command_palette",
        "description": "Open command palette",
        "category": "commands",
    },
    {
        "key": "ctrl+k",
        "action": "quick_command",
        "description": "Quick command",
        "category": "commands",
    },
    {
        "key": "<leader> h",
        "action": "show_help",
        "description": "Show help",
        "category": "dialogs",
    },
    {
        "key": "<leader> w",
        "action": "show_workflows",
        "description": "Show workflow demo",
        "category": "dialogs",
    },
    {
        "key": "<leader> e",
        "action": "show_events",
        "description": "Show event stream",
        "category": "dialogs",
    },
    {
        "key": "<leader> b",
        "action": "show_memory",
        "description": "Show memory browser",
        "category": "dialogs",
    },
    {
        "key": "<leader> n",
        "action": "new_session",
        "description": "New session",
        "category": "session",
    },
    {
        "key": "<leader> l",
        "action": "list_sessions",
        "description": "List sessions",
        "category": "session",
    },
    {
        "key": "ctrl+shift+s",
        "action": "save_session",
        "description": "Save session",
        "category": "session",
    },
    {
        "key": "<leader> d",
        "action": "toggle_dark_mode",
        "description": "Toggle dark/light mode",
        "category": "theme",
    },
    {
        "key": "<leader> c",
        "action": "cycle_theme",
        "description": "Cycle themes",
        "category": "theme",
    },
    {
        "key": "ctrl+shift+c",
        "action": "copy_selection",
        "description": "Copy selection",
        "category": "clipboard",
    },
    {
        "key": "ctrl+shift+v",
        "action": "paste_smart",
        "description": "Smart paste",
        "category": "clipboard",
    },
]


@dataclass
class KeybindConfig:
    """Configuration for keybindings."""

    keybinds: List[Dict[str, Any]] = field(
        default_factory=lambda: DEFAULT_KEYBINDS.copy()
    )
    leader_key: str = "ctrl+space"
    leader_timeout: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "keybinds": self.keybinds,
            "leader_key": self.leader_key,
            "leader_timeout": self.leader_timeout,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> KeybindConfig:
        """Create from dictionary."""
        return cls(
            keybinds=data.get("keybinds", DEFAULT_KEYBINDS.copy()),
            leader_key=data.get("leader_key", "ctrl+space"),
            leader_timeout=data.get("leader_timeout", 2.0),
        )

    def get_keybind_infos(self) -> List[KeybindInfo]:
        """Convert to list of KeybindInfo objects."""
        result = []
        for kb_data in self.keybinds:
            result.append(
                KeybindInfo(
                    key=kb_data["key"],
                    action=kb_data["action"],
                    description=kb_data.get("description", ""),
                    category=kb_data.get("category", "general"),
                    show_in_help=kb_data.get("show_in_help", True),
                    context=kb_data.get("context"),
                )
            )
        return result

    def add_keybind(self, keybind: Dict[str, Any]) -> None:
        """Add a keybind."""
        self.keybinds = [kb for kb in self.keybinds if kb["key"] != keybind["key"]]
        self.keybinds.append(keybind)

    def remove_keybind(self, key: str) -> bool:
        """Remove a keybind by key."""
        original_len = len(self.keybinds)
        self.keybinds = [kb for kb in self.keybinds if kb["key"] != key]
        return len(self.keybinds) < original_len

    def reset_to_defaults(self) -> None:
        """Reset to default keybindings."""
        self.keybinds = DEFAULT_KEYBINDS.copy()
        self.leader_key = "ctrl+space"
        self.leader_timeout = 2.0


DEFAULT_CONFIG_PATH = Path("~/.aura/tui_keybinds.json").expanduser()


def load_keybinds(config_path: Optional[Path] = None) -> KeybindConfig:
    """
    Load keybind configuration from file.

    Args:
        config_path: Path to config file (uses default if not provided)

    Returns:
        KeybindConfig instance
    """
    path = config_path or DEFAULT_CONFIG_PATH

    if not path.exists():
        return KeybindConfig()

    try:
        with open(path) as f:
            data = json.load(f)
        return KeybindConfig.from_dict(data)
    except Exception as e:
        logger.warning(f"Failed to load keybind config: {e}")
        return KeybindConfig()


def save_keybinds(config: KeybindConfig, config_path: Optional[Path] = None) -> bool:
    """
    Save keybind configuration to file.

    Args:
        config: KeybindConfig to save
        config_path: Path to config file (uses default if not provided)

    Returns:
        True if successful
    """
    path = config_path or DEFAULT_CONFIG_PATH

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(config.to_dict(), f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save keybind config: {e}")
        return False


def merge_with_defaults(config: KeybindConfig) -> KeybindConfig:
    """
    Merge user config with defaults (adds missing defaults).

    Args:
        config: User configuration

    Returns:
        Merged configuration
    """
    existing_keys = {kb["key"] for kb in config.keybinds}

    for default_kb in DEFAULT_KEYBINDS:
        if default_kb["key"] not in existing_keys:
            config.keybinds.append(default_kb)

    return config


class KeybindPersistence:
    """Persistent storage and retrieval of keybind configurations.

    Supports auto-save on changes, named profiles (import/export) and
    undo/redo history (up to 50 steps). Config is stored under
    ~/.aura/keybinds/ by default.
    """

    def __init__(self, config_dir: Optional[Path] = None, auto_save: bool = True):
        """Initialize the keybind manager with config directory and undo history."""
        self.config_dir = config_dir or Path("~/.aura/keybinds").expanduser()
        self.auto_save = auto_save
        self._config: KeybindConfig = KeybindConfig()
        self._history: List[Dict[str, Any]] = []
        self._history_index: int = -1
        self._max_history: int = 50
        self._dirty: bool = False

        self.config_dir.mkdir(parents=True, exist_ok=True)
        self._load_default()

    @property
    def config(self) -> KeybindConfig:
        """Get current keybind configuration."""
        return self._config

    @property
    def default_config_path(self) -> Path:
        """Get path to default config file."""
        return self.config_dir / "default.json"

    def _load_default(self) -> None:
        """Load default configuration."""
        if self.default_config_path.exists():
            self._config = load_keybinds(self.default_config_path)
        else:
            self._config = KeybindConfig()

    def load(self, config_path: Optional[Path] = None) -> KeybindConfig:
        """
        Load keybind configuration.

        Args:
            config_path: Optional path (uses default if not provided)

        Returns:
            Loaded configuration
        """
        path = config_path or self.default_config_path
        self._config = load_keybinds(path)
        self._config = merge_with_defaults(self._config)
        self._dirty = False
        return self._config

    def save(self, config_path: Optional[Path] = None) -> bool:
        """
        Save current keybind configuration.

        Args:
            config_path: Optional path (uses default if not provided)

        Returns:
            True if successful
        """
        path = config_path or self.default_config_path
        success = save_keybinds(self._config, path)
        if success:
            self._dirty = False
            logger.info(f"Keybinds saved to {path}")
        return success

    def _auto_save(self) -> None:
        """Auto-save if enabled."""
        if self.auto_save and self._dirty:
            self.save()

    def _save_to_history(self) -> None:
        """Save current state to history for undo."""
        if self._history_index < len(self._history) - 1:
            self._history = self._history[: self._history_index + 1]

        self._history.append(self._config.to_dict())

        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        self._history_index = len(self._history) - 1

    def set_keybind(
        self,
        key: str,
        action: str,
        description: str = "",
        category: str = "custom",
        **kwargs,
    ) -> None:
        """
        Set or update a keybind.

        Args:
            key: Key combination (e.g., "ctrl+n")
            action: Action name
            description: Human-readable description
            category: Keybind category
            **kwargs: Additional keybind properties
        """
        self._save_to_history()

        keybind = {
            "key": key,
            "action": action,
            "description": description,
            "category": category,
            **kwargs,
        }
        self._config.add_keybind(keybind)
        self._dirty = True
        self._auto_save()

        logger.debug(f"Set keybind: {key} -> {action}")

    def remove_keybind(self, key: str) -> bool:
        """
        Remove a keybind.

        Args:
            key: Key combination to remove

        Returns:
            True if removed
        """
        self._save_to_history()

        removed = self._config.remove_keybind(key)
        if removed:
            self._dirty = True
            self._auto_save()
            logger.debug(f"Removed keybind: {key}")
        return removed

    def get_keybind(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a keybind by key.

        Args:
            key: Key combination

        Returns:
            Keybind dict or None
        """
        for kb in self._config.keybinds:
            if kb["key"] == key:
                return kb
        return None

    def get_keybinds_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all keybinds in a category."""
        return [kb for kb in self._config.keybinds if kb.get("category") == category]

    def get_keybinds_by_action(self, action: str) -> List[Dict[str, Any]]:
        """Get all keybinds for an action."""
        return [kb for kb in self._config.keybinds if kb["action"] == action]

    def undo(self) -> bool:
        """
        Undo last keybind change.

        Returns:
            True if undo was performed
        """
        if self._history_index <= 0:
            return False

        self._history_index -= 1
        self._config = KeybindConfig.from_dict(self._history[self._history_index])
        self._dirty = True
        self._auto_save()

        logger.debug("Undid keybind change")
        return True

    def redo(self) -> bool:
        """
        Redo last undone change.

        Returns:
            True if redo was performed
        """
        if self._history_index >= len(self._history) - 1:
            return False

        self._history_index += 1
        self._config = KeybindConfig.from_dict(self._history[self._history_index])
        self._dirty = True
        self._auto_save()

        logger.debug("Redid keybind change")
        return True

    def reset_to_defaults(self) -> None:
        """Reset all keybinds to defaults."""
        self._save_to_history()
        self._config.reset_to_defaults()
        self._dirty = True
        self._auto_save()
        logger.info("Reset keybinds to defaults")

    def list_profiles(self) -> List[str]:
        """List available keybind profiles."""
        profiles = []
        for path in self.config_dir.glob("*.json"):
            profiles.append(path.stem)
        return profiles

    def save_profile(self, name: str) -> bool:
        """
        Save current config as a named profile.

        Args:
            name: Profile name

        Returns:
            True if successful
        """
        path = self.config_dir / f"{name}.json"
        return self.save(path)

    def load_profile(self, name: str) -> bool:
        """
        Load a named profile.

        Args:
            name: Profile name

        Returns:
            True if successful
        """
        path = self.config_dir / f"{name}.json"
        if not path.exists():
            logger.warning(f"Profile not found: {name}")
            return False

        self.load(path)
        return True

    def delete_profile(self, name: str) -> bool:
        """
        Delete a profile.

        Args:
            name: Profile name

        Returns:
            True if deleted
        """
        if name == "default":
            logger.warning("Cannot delete default profile")
            return False

        path = self.config_dir / f"{name}.json"
        if path.exists():
            path.unlink()
            logger.info(f"Deleted profile: {name}")
            return True
        return False

    def export_keybinds(self, path: Path) -> bool:
        """
        Export keybinds to a file.

        Args:
            path: Export path

        Returns:
            True if successful
        """
        try:
            with open(path, "w") as f:
                json.dump(self._config.to_dict(), f, indent=2)
            logger.info(f"Exported keybinds to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export keybinds: {e}")
            return False

    def import_keybinds(self, path: Path, merge: bool = True) -> bool:
        """
        Import keybinds from a file.

        Args:
            path: Import path
            merge: If True, merge with existing. If False, replace.

        Returns:
            True if successful
        """
        try:
            with open(path) as f:
                data = json.load(f)

            self._save_to_history()

            if merge:
                imported = KeybindConfig.from_dict(data)
                for kb in imported.keybinds:
                    self._config.add_keybind(kb)
            else:
                self._config = KeybindConfig.from_dict(data)

            self._dirty = True
            self._auto_save()

            logger.info(f"Imported keybinds from {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to import keybinds: {e}")
            return False


_persistence: Optional[KeybindPersistence] = None


def get_keybind_persistence() -> KeybindPersistence:
    """Get the global keybind persistence instance."""
    global _persistence
    if _persistence is None:
        _persistence = KeybindPersistence()
    return _persistence
