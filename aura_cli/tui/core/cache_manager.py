"""Cache and Settings Manager for Aura TUI.

Persistent settings storage with JSON serialization and scope management.

Features:
- Persistent settings storage in ~/.aura/cache
- Scoped settings (global, per-file, etc.)
- Default settings with fallback
- Import/export functionality
- Automatic directory creation
- Error handling with logging

Storage:
- Location: ~/.aura/cache/settings.json
- Format: JSON with scoped settings
- Defaults: Theme, UI preferences, auto-save config
"""

import json
import logging
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

logger = logging.getLogger(__name__)

from aura_cli.core.paths import aura_path

CACHE_DIR = aura_path("cache")
SETTINGS_FILE = CACHE_DIR / "settings.json"


class CacheManager:
    """Application settings and cache manager.

    Provides persistent storage for TUI settings with automatic
    directory creation, scope management, and error handling.
    """

    DEFAULT_SETTINGS: ClassVar[Dict[str, Any]] = {
        "theme": "nebula-dark",
        "input_width": 50,
        "show_preview": True,
        "sidebar_visible": True,
        "active_panel": "events",
        "font_size": "medium",
        "show_line_numbers": True,
        "auto_save": True,
        "auto_save_interval": 60,
    }

    def __init__(self):
        """Initialize the instance."""
        self._ensure_cache_dir()
        self._settings: Dict[str, Dict[str, Any]] = {}
        self._load_all_settings()

    def _ensure_cache_dir(self) -> None:
        """Ensure cache directory exists."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    def _load_all_settings(self) -> None:
        """Load all settings from disk."""
        try:
            if SETTINGS_FILE.exists():
                content = SETTINGS_FILE.read_text(encoding="utf-8")
                self._settings = json.loads(content)
                logger.debug(f"Loaded settings from {SETTINGS_FILE}")
            else:
                self._settings = {"global": self.DEFAULT_SETTINGS.copy()}
                self._save_all_settings()
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"Error loading settings: {e}, using defaults")
            self._settings = {"global": self.DEFAULT_SETTINGS.copy()}

    def _save_all_settings(self) -> None:
        """Save all settings to disk."""
        try:
            self._ensure_cache_dir()
            SETTINGS_FILE.write_text(
                json.dumps(self._settings, indent=2), encoding="utf-8"
            )
            logger.debug(f"Saved settings to {SETTINGS_FILE}")
        except OSError as e:
            logger.error(f"Error saving settings: {e}")

    def get(self, key: str, scope: str = "global", default: Any = None) -> Any:
        """
        Get a setting value.

        Args:
            key: Setting key
            scope: Settings scope (global or file path)
            default: Default value if not found

        Returns:
            Setting value or default
        """
        scope_settings = self._settings.get(scope, {})
        if key in scope_settings:
            return scope_settings[key]

        if scope != "global":
            global_settings = self._settings.get("global", {})
            if key in global_settings:
                return global_settings[key]

        if default is None and key in self.DEFAULT_SETTINGS:
            return self.DEFAULT_SETTINGS[key]

        return default

    def set(self, key: str, value: Any, scope: str = "global") -> None:
        """
        Set a setting value.

        Args:
            key: Setting key
            value: Value to set
            scope: Settings scope
        """
        if scope not in self._settings:
            self._settings[scope] = {}
        self._settings[scope][key] = value
        self._save_all_settings()

    def get_scope_settings(self, scope: str = "global") -> Dict[str, Any]:
        """Get all settings for a scope with defaults applied."""
        defaults = self.DEFAULT_SETTINGS.copy()
        global_settings = self._settings.get("global", {})
        scope_settings = self._settings.get(scope, {})

        return {**defaults, **global_settings, **scope_settings}

    def save_scope_settings(self, scope: str, settings: Dict[str, Any]) -> None:
        """Save all settings for a scope."""
        self._settings[scope] = settings
        self._save_all_settings()

    def remove_scope(self, scope: str) -> bool:
        """Remove settings for a scope."""
        if scope in self._settings and scope != "global":
            del self._settings[scope]
            self._save_all_settings()
            return True
        return False

    def list_scopes(self) -> List[str]:
        """List all settings scopes."""
        return list(self._settings.keys())

    def reset_scope(self, scope: str = "global") -> None:
        """Reset scope to default settings."""
        if scope == "global":
            self._settings[scope] = self.DEFAULT_SETTINGS.copy()
        else:
            self._settings.pop(scope, None)
        self._save_all_settings()

    def export_settings(self, filepath: Path) -> bool:
        """Export settings to a file."""
        try:
            filepath.write_text(json.dumps(self._settings, indent=2), encoding="utf-8")
            return True
        except OSError as e:
            logger.error(f"Error exporting settings: {e}")
            return False

    def import_settings(self, filepath: Path, merge: bool = True) -> bool:
        """
        Import settings from a file.

        Args:
            filepath: Path to settings file
            merge: If True, merge with existing; if False, replace

        Returns:
            True if successful
        """
        try:
            content = filepath.read_text(encoding="utf-8")
            imported = json.loads(content)

            if merge:
                for scope, settings in imported.items():
                    if scope not in self._settings:
                        self._settings[scope] = {}
                    self._settings[scope].update(settings)
            else:
                self._settings = imported

            self._save_all_settings()
            return True
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Error importing settings: {e}")
            return False


_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get global CacheManager instance."""
    global _manager
    if _manager is None:
        _manager = CacheManager()
    return _manager
