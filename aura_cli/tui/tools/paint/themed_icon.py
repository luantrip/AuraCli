"""Themed Icon Widget - Aura CLI Paint Tool.

Static widget that automatically switches content based on light/dark theme.

Features:
    - Automatic theme detection
    - Separate renderables for light/dark themes
    - Rich renderable support
    - Reactive theme switching
"""

from rich.console import RenderableType
from rich.protocol import is_renderable
from textual.errors import RenderError
from textual.widgets import Static


def _check_renderable(renderable: object):
    """Validate Rich renderable protocol compliance.

    Args:
        renderable: Object to validate

    Raises:
        RenderError: If object cannot be rendered
    """
    if not is_renderable(renderable):
        raise RenderError(
            f"unable to render {renderable!r}; a string, Text, or other Rich renderable is required"
        )


class ThemedIcon(Static):
    """Static widget with theme-aware content switching.

    Automatically updates displayed content when theme changes
    between light and dark modes.

    Args:
        light_renderable: Content for light theme
        dark_renderable: Content for dark theme
        name: Widget name
        id: Widget ID
        classes: Space-separated class names
        disabled: Whether widget is disabled
    """

    def __init__(
        self,
        light_renderable: RenderableType,
        dark_renderable: RenderableType,
        *,
        name: str | None = None,
        icon_id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        """Initialize themed icon widget.

        Args:
            light_renderable: Content for light theme
            dark_renderable: Content for dark theme
            name: Widget name
            id: Widget ID
            classes: CSS classes
            disabled: Disabled state
        """
        super().__init__(
            "",
            name=name,
            id=icon_id,
            classes=classes,
            disabled=disabled,
        )
        self.light_renderable = light_renderable
        self.dark_renderable = dark_renderable
        _check_renderable(light_renderable)
        _check_renderable(dark_renderable)
        self.watch(self.app, "dark", self._on_dark_changed, init=False)
        self._on_dark_changed(False, self.app.dark)

    def _on_dark_changed(self, _old_value: bool, dark: bool) -> None:
        """Handle theme change.

        Args:
            _old_value: Previous dark mode state (required by Textual watcher API)
            dark: New dark mode state
        """
        if dark:
            self.update(self.dark_renderable)
        else:
            self.update(self.light_renderable)
