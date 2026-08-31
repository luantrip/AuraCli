"""Monitor configuration management.

Handles loading, saving, and managing monitor configuration.

Features:
    - TOML-based configuration
    - Default configuration generation
    - Display settings (color, images, terminal size)
    - Network settings (user agent, timeout, redirects)
    - Feature toggles (cookies, JavaScript, images, history)
    - Custom keybindings
    - Configuration validation

Classes:
    MonitorConfig: Configuration dataclass with defaults
"""

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, Optional

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore

try:
    import tomli_w

    HAS_TOMLI_W = True
except ImportError:
    HAS_TOMLI_W = False


# =============================================================================
# DEFAULT CONFIGURATION
# =============================================================================

DEFAULT_CONFIG = """
# Aura Monitor Configuration
# ==========================

[display]
# Color mode: auto, true, 256, 16, mono
color_mode = "auto"

# Image rendering: auto, sixel, kitty, none
image_mode = "auto"

# Terminal size (0 = auto-detect)
columns = 0
lines = 0

# UI colors
highlight_color = "cyan"
background = "default"

[network]
# User agent string
user_agent = "Aura-Monitor/1.0"

# Request timeout in seconds
timeout = 30

# Maximum redirects to follow
max_redirects = 10

[features]
# Enable cookies
cookies = false

# Enable JavaScript
javascript = false

# Enable images
images = false

# Enable history
history = true

[keybindings]
# Custom keybindings (Vim-style by default)
quit = "q"
back = "b"
forward = "l"
reload = "r"
scroll_down = "j"
scroll_up = "k"
page_down = "ctrl+f"
page_up = "ctrl+b"
goto_url = "g"
search = "/"

[bookmarks]
# Quick access URLs
home = "about:blank"
search = "https://lite.duckduckgo.com/lite/"

[monitoring]
# Auto-refresh interval in seconds (0 = disabled)
refresh_interval = 0

# URLs to monitor
watch_urls = []
"""


@dataclass
class DisplayConfig:
    """Display configuration."""

    color_mode: str = "auto"
    image_mode: str = "auto"
    columns: int = 0
    lines: int = 0
    highlight_color: str = "cyan"
    background: str = "default"


@dataclass
class NetworkConfig:
    """Network configuration."""

    user_agent: str = "Aura-Monitor/1.0"
    timeout: int = 30
    max_redirects: int = 10


@dataclass
class FeaturesConfig:
    """Features configuration."""

    cookies: bool = False
    javascript: bool = False
    images: bool = False
    history: bool = True


@dataclass
class KeybindingsConfig:
    """Keybindings configuration."""

    quit: str = "q"
    back: str = "b"
    forward: str = "l"
    reload: str = "r"
    scroll_down: str = "j"
    scroll_up: str = "k"
    page_down: str = "ctrl+f"
    page_up: str = "ctrl+b"
    goto_url: str = "g"
    search: str = "/"


@dataclass
class BookmarksConfig:
    """Bookmarks configuration."""

    home: str = "about:blank"
    search: str = "https://lite.duckduckgo.com/lite/"


@dataclass
class MonitoringConfig:
    """Monitoring configuration."""

    refresh_interval: int = 0
    watch_urls: list = field(default_factory=list)


@dataclass
class FullMonitorConfig:
    """Complete monitor configuration."""

    display: DisplayConfig = field(default_factory=DisplayConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    keybindings: KeybindingsConfig = field(default_factory=KeybindingsConfig)
    bookmarks: BookmarksConfig = field(default_factory=BookmarksConfig)
    monitoring: MonitoringConfig = field(default_factory=MonitoringConfig)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "display": asdict(self.display),
            "network": asdict(self.network),
            "features": asdict(self.features),
            "keybindings": asdict(self.keybindings),
            "bookmarks": asdict(self.bookmarks),
            "monitoring": asdict(self.monitoring),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "FullMonitorConfig":
        """Create from dictionary."""
        return cls(
            display=DisplayConfig(**data.get("display", {})),
            network=NetworkConfig(**data.get("network", {})),
            features=FeaturesConfig(**data.get("features", {})),
            keybindings=KeybindingsConfig(**data.get("keybindings", {})),
            bookmarks=BookmarksConfig(**data.get("bookmarks", {})),
            monitoring=MonitoringConfig(**data.get("monitoring", {})),
        )


# =============================================================================
# CONFIG MANAGER
# =============================================================================


class MonitorConfigManager:
    """Manages monitor configuration."""

    DEFAULT_CONFIG_DIR = Path.home() / ".config" / "aura"
    CONFIG_FILENAME = "monitor.toml"

    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or self.DEFAULT_CONFIG_DIR
        self.config_path = self.config_dir / self.CONFIG_FILENAME
        self._config: Optional[FullMonitorConfig] = None

    @property
    def config(self) -> FullMonitorConfig:
        """Get current configuration (lazy load)."""
        if self._config is None:
            self._config = self.load()
        return self._config

    def ensure_config_dir(self) -> None:
        """Ensure config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def load(self) -> FullMonitorConfig:
        """Load configuration from file."""
        if not self.config_path.exists():
            return FullMonitorConfig()

        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)
            return FullMonitorConfig.from_dict(data)
        except Exception as e:
            print(f"Warning: Failed to load monitor config: {e}")
            return FullMonitorConfig()

    def save(self, config: Optional[FullMonitorConfig] = None) -> bool:
        """Save configuration to file."""
        if config is None:
            config = self._config or FullMonitorConfig()

        self.ensure_config_dir()

        try:
            if HAS_TOMLI_W:
                with open(self.config_path, "wb") as f:
                    tomli_w.dump(config.to_dict(), f)
            else:
                # Fallback: write as JSON
                json_path = self.config_dir / "monitor.json"
                with open(json_path, "w") as f:
                    json.dump(config.to_dict(), f, indent=2)
            return True
        except Exception as e:
            print(f"Warning: Failed to save monitor config: {e}")
            return False

    def reset_to_defaults(self) -> FullMonitorConfig:
        """Reset configuration to defaults."""
        self._config = FullMonitorConfig()
        self.save(self._config)
        return self._config

    def write_default_config(self) -> None:
        """Write default config file."""
        self.ensure_config_dir()
        with open(self.config_path, "w") as f:
            f.write(DEFAULT_CONFIG)


# Global config manager instance
_config_manager: Optional[MonitorConfigManager] = None


def get_config_manager() -> MonitorConfigManager:
    """Get the global config manager."""
    global _config_manager
    if _config_manager is None:
        _config_manager = MonitorConfigManager()
    return _config_manager


def get_monitor_config() -> FullMonitorConfig:
    """Get the current monitor configuration."""
    return get_config_manager().config
