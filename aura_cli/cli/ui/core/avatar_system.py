"""
Avatar System - Visual identity for chat participants.

Provides consistent visual representation for users, agents,
and system messages with customizable styles.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

from rich.text import Text

from aura_cli.cli.ui.theme_manager import get_theme_manager


class AvatarStyle(str, Enum):
    """Avatar display styles."""

    ICON = "icon"
    INITIAL = "initial"
    BADGE = "badge"
    MINIMAL = "minimal"


@dataclass
class Avatar:
    """Represents a chat participant's visual identity."""

    name: str
    icon: str
    color: str
    style: AvatarStyle = AvatarStyle.ICON
    secondary_color: Optional[str] = None

    def render(self, size: str = "normal") -> Text:
        """
        Render the avatar as Rich Text.

        Args:
            size: "compact", "normal", or "large"

        Returns:
            Styled Text representation
        """
        get_theme_manager()
        result = Text()

        if self.style == AvatarStyle.ICON:
            result.append(self.icon, style=f"bold {self.color}")
            if size != "compact":
                result.append(" ")

        elif self.style == AvatarStyle.INITIAL:
            initial = self.name[0].upper()
            result.append(f"[{initial}]", style=f"bold {self.color}")
            if size != "compact":
                result.append(" ")

        elif self.style == AvatarStyle.BADGE:
            result.append(f" {self.icon} ", style=f"reverse bold {self.color}")
            if size != "compact":
                result.append(" ")

        elif self.style == AvatarStyle.MINIMAL:
            result.append("▸", style=f"{self.color}")
            if size != "compact":
                result.append(" ")

        return result

    def render_with_name(
        self, show_time: bool = False, timestamp: Optional[str] = None
    ) -> Text:
        """
        Render avatar with name and optional timestamp.

        Args:
            show_time: Whether to show timestamp
            timestamp: Optional timestamp string

        Returns:
            Full header Text
        """
        result = self.render()
        result.append(self.name, style=f"bold {self.color}")

        if show_time and timestamp:
            result.append(f" {timestamp}", style="dim italic")

        return result


class AvatarSystem:
    """
    Manages avatars for different chat participants.

    Provides consistent visual identity across the application with caching.
    """

    def __init__(self):
        """Initialize the instance."""
        self._avatars: Dict[str, Avatar] = {}
        self._render_cache: Dict[str, Text] = {}
        self._setup_default_avatars()

    def _setup_default_avatars(self) -> None:
        """Setup default system avatars."""
        theme = get_theme_manager()

        self._avatars.update(
            {
                "user": Avatar(
                    name="You",
                    icon="▶",
                    color=theme.get_color("primary"),
                    style=AvatarStyle.ICON,
                ),
                "assistant": Avatar(
                    name="Aura",
                    icon="✦",
                    color=theme.get_color("accent"),
                    style=AvatarStyle.ICON,
                ),
                "aura": Avatar(
                    name="Aura",
                    icon="✦",
                    color=theme.get_color("accent"),
                    style=AvatarStyle.ICON,
                ),
                "system": Avatar(
                    name="System",
                    icon="●",
                    color=theme.get_color("muted"),
                    style=AvatarStyle.MINIMAL,
                ),
                "agi": Avatar(
                    name="AGI",
                    icon="◈",
                    color=theme.get_color("secondary"),
                    style=AvatarStyle.BADGE,
                ),
                "ops": Avatar(
                    name="OPS",
                    icon="✦",
                    color=theme.get_color("warning"),
                    style=AvatarStyle.BADGE,
                ),
                "tool": Avatar(
                    name="Ferramenta",
                    icon="⚒",
                    color=theme.get_color("warning"),
                    style=AvatarStyle.ICON,
                ),
                "error": Avatar(
                    name="Erro",
                    icon="✖",
                    color=theme.get_color("error"),
                    style=AvatarStyle.ICON,
                ),
                "success": Avatar(
                    name="Sucesso",
                    icon="✔",
                    color=theme.get_color("success"),
                    style=AvatarStyle.ICON,
                ),
            }
        )

    def get(self, name: str) -> Avatar:
        """
        Get avatar by name.

        Args:
            name: Avatar identifier

        Returns:
            Avatar instance (default system avatar if not found)
        """
        key = name.lower()
        return self._avatars.get(key, self._avatars["system"])

    def register(self, key: str, avatar: Avatar) -> None:
        """Register a custom avatar."""
        self._avatars[key.lower()] = avatar

    def create(
        self,
        name: str,
        icon: str,
        color: str,
        style: AvatarStyle = AvatarStyle.ICON,
    ) -> Avatar:
        """Create and register a new avatar."""
        avatar = Avatar(name=name, icon=icon, color=color, style=style)
        self._avatars[name.lower()] = avatar
        return avatar

    def list_avatars(self) -> List[str]:
        """List all registered avatar keys."""
        return list(self._avatars.keys())

    def render_header(
        self,
        sender: str,
        timestamp: Optional[str] = None,
        badge: Optional[str] = None,
    ) -> Text:
        """
        Render a full message header with avatar (cached).

        Args:
            sender: Sender identifier
            timestamp: Optional timestamp
            badge: Optional badge text (e.g., "THINKING", "TYPING")

        Returns:
            Complete header Text
        """
        # Cache key
        cache_key = f"{sender}_{timestamp}_{badge}"

        if cache_key in self._render_cache:
            return self._render_cache[cache_key]

        avatar = self.get(sender)
        result = avatar.render_with_name(
            show_time=timestamp is not None,
            timestamp=timestamp,
        )

        if badge:
            theme = get_theme_manager()
            result.append(" ")
            result.append(f" {badge} ", style=f"reverse dim {theme.get_color('muted')}")

        # Cache the rendering
        self._render_cache[cache_key] = result

        return result

    def clear_cache(self):
        """Clear the render cache."""
        self._render_cache.clear()


_system: Optional[AvatarSystem] = None


def get_avatar_system() -> AvatarSystem:
    """Get global AvatarSystem instance."""
    global _system
    if _system is None:
        _system = AvatarSystem()
    return _system
