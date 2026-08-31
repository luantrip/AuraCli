"""
Plugin SDK for Aura TUI.

Provides a complete SDK for building custom TUI plugins with:
- Widget creation helpers
- Event integration
- Theme-aware styling
- Lifecycle management

Usage:
    from aura_cli.tui.plugins.sdk import (
        PluginWidget,
        register_plugin,
        plugin_command,
        on_event,
    )

    @register_plugin("my-plugin")
    class MyPlugin(PluginWidget):
        def compose(self):
            yield Static("Hello from plugin!")
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Type

from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget

from aura_cli.application.extensions import PluginMetadata

if TYPE_CHECKING:
    from textual.app import App, ComposeResult

logger = logging.getLogger(__name__)


@dataclass
class PluginInfo(PluginMetadata):
    """Metadata about a plugin."""

    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "homepage": self.homepage,
            "tags": self.tags,
            "dependencies": self.dependencies,
        }


@dataclass
class PluginCommand:
    """A command provided by a plugin."""

    name: str
    description: str
    callback: Callable
    keybind: Optional[str] = None
    category: str = "Plugin"

    def execute(self, *args, **kwargs):
        """Execute the command."""
        return self.callback(*args, **kwargs)


class PluginWidget(Widget):
    """Base class for TUI plugin widgets.

    Provides automatic event-bus integration, theme-aware styling,
    lifecycle hooks and command registration. Set PLUGIN_INFO to
    declare the plugin's name and version.
    """

    PLUGIN_INFO: Optional[PluginInfo] = None
    DEFAULT_CSS = ""

    is_active: reactive[bool] = reactive(True)

    def __init__(self, *args, plugin_id: str | None = None, **kwargs):
        """Initialize the instance."""
        super().__init__(*args, **kwargs)
        self._plugin_id = plugin_id or (
            self.PLUGIN_INFO.name if self.PLUGIN_INFO else "unnamed"
        )
        self._commands: List[PluginCommand] = []
        self._event_subscriptions: List[Callable] = []
        self._initialized = False

    @property
    def plugin_id(self) -> str:
        """Get the plugin ID."""
        return self._plugin_id

    @property
    def info(self) -> Optional[PluginInfo]:
        """Get plugin info."""
        return self.PLUGIN_INFO

    @property
    def commands(self) -> List[PluginCommand]:
        """Get plugin commands."""
        return self._commands

    def on_mount(self) -> None:
        """Called when widget is mounted."""
        super().on_mount()  # type: ignore[misc]

        if not self._initialized:
            self._initialize()
            self._initialized = True

        self.on_plugin_mount()

    def on_unmount(self) -> None:
        """Called when widget is unmounted."""
        self.on_plugin_unmount()
        self._cleanup()
        super().on_unmount()  # type: ignore[misc]

    def _initialize(self) -> None:
        """Initialize plugin systems."""
        self._setup_event_subscriptions()
        self._register_commands()

        logger.debug(f"Plugin {self._plugin_id} initialized")

    def _cleanup(self) -> None:
        """Cleanup plugin resources."""
        for unsub in self._event_subscriptions:
            with contextlib.suppress(Exception):
                unsub()
        self._event_subscriptions.clear()

        logger.debug(f"Plugin {self._plugin_id} cleaned up")

    def _setup_event_subscriptions(self) -> None:
        """Set up event bus subscriptions."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if hasattr(attr, "_event_subscription"):
                event_name = attr._event_subscription  # type: ignore
                self._subscribe_to_event(event_name, attr)  # type: ignore[arg-type]

    def _subscribe_to_event(self, event_name: str, handler: Callable) -> None:
        """Subscribe to an event."""
        try:
            from aura_cli.tui.core.event_bus import TUIEvents

            unsub = TUIEvents.bus.subscribe(event_name, handler)
            self._event_subscriptions.append(unsub)
        except Exception as e:
            logger.error(f"Failed to subscribe to {event_name}: {e}")

    def _register_commands(self) -> None:
        """Register plugin commands."""
        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if callable(attr) and hasattr(attr, "_plugin_command"):
                cmd_info = attr._plugin_command
                command = PluginCommand(
                    name=cmd_info["name"],
                    description=cmd_info["description"],
                    callback=attr,
                    keybind=cmd_info.get("keybind"),
                    category=cmd_info.get("category", "Plugin"),
                )
                self._commands.append(command)

    def on_plugin_mount(self) -> None:
        """Called when plugin is mounted. Override to add custom behavior."""

    def on_plugin_unmount(self) -> None:
        """Called when plugin is unmounted. Override to add cleanup."""

    def emit_event(
        self, event_name: str, payload: Dict[str, Any] | None = None
    ) -> None:
        """
        Emit an event to the event bus.

        Args:
            event_name: Name of the event (will be prefixed with plugin.{id}.)
            payload: Event payload
        """
        try:
            from aura_cli.tui.core.event_bus import TUIEvents

            full_name = f"plugin.{self._plugin_id}.{event_name}"
            TUIEvents.bus.publish(full_name, payload or {})
        except Exception as e:
            logger.error(f"Failed to emit event {event_name}: {e}")

    def show_toast(self, message: str, severity: str = "information") -> None:
        """
        Show a toast notification.

        Args:
            message: Notification message
            severity: One of "information", "warning", "error"
        """
        try:
            from aura_cli.tui.core.event_bus import show_toast

            show_toast(message, severity=severity)  # type: ignore
        except Exception:
            self.app.notify(message, severity=severity)  # type: ignore[arg-type]

    def get_store(self):
        """Get the sync store."""
        try:
            from aura_cli.tui.core.sync_store import get_store

            return get_store()
        except Exception:
            return None

    def get_theme_manager(self):
        """Get the theme manager."""
        try:
            from aura_cli.tui.styles.themes import get_theme_manager

            return get_theme_manager()
        except Exception:
            return None


def plugin_command(
    name: str,
    description: str = "",
    keybind: str | None = None,
    category: str = "Plugin",
):
    """
    Decorator to register a method as a plugin command.

    Args:
        name: Command name
        description: Command description
        keybind: Optional keybind string
        category: Command category

    Example:
        ```python
        @plugin_command("greet", "Say hello", keybind="ctrl+g")
        def greet(self):
            self.show_toast("Hello!")
        ```
    """

    def decorator(func: Callable) -> Callable:
        """Decorator factory for plugin registration."""
        func._plugin_command = {  # type: ignore[attr-defined]
            "name": name,
            "description": description,
            "keybind": keybind,
            "category": category,
        }
        return func

    return decorator


def on_event(event_name: str):
    """
    Decorator to subscribe a method to an event.

    Args:
        event_name: Event name to subscribe to

    Example:
        ```python
        @on_event("tui.toast.show")
        def handle_toast(self, payload):
            self.log.info(f"Toast: {payload}")
        ```
    """

    def decorator(func: Callable) -> Callable:
        """Decorator factory for plugin registration."""
        func._event_subscription = event_name  # type: ignore[attr-defined]
        return func

    return decorator


class PluginRegistry:
    """Registry for managing plugins."""

    def __init__(self):
        """Initialize the instance."""
        self._plugins: Dict[str, Type[PluginWidget]] = {}
        self._instances: Dict[str, PluginWidget] = {}

    def register(self, plugin_class: Type[PluginWidget]) -> None:
        """
        Register a plugin class.

        Args:
            plugin_class: Plugin class to register
        """
        if plugin_class.PLUGIN_INFO:
            name = plugin_class.PLUGIN_INFO.name
        else:
            name = plugin_class.__name__

        self._plugins[name] = plugin_class
        logger.info(f"Registered plugin: {name}")

    def get(self, name: str) -> Optional[Type[PluginWidget]]:
        """Get a registered plugin class by name."""
        return self._plugins.get(name)

    def instantiate(
        self, name: str, app: Optional[App] = None, **kwargs
    ) -> Optional[PluginWidget]:
        """
        Create an instance of a plugin.

        Args:
            name: Plugin name
            app: Optional app instance
            **kwargs: Additional arguments for plugin

        Returns:
            Plugin instance or None
        """
        plugin_class = self._plugins.get(name)
        if not plugin_class:
            logger.warning(f"Plugin not found: {name}")
            return None

        try:
            instance = plugin_class(**kwargs)
            self._instances[name] = instance
            return instance
        except Exception as e:
            logger.error(f"Failed to instantiate plugin {name}: {e}")
            return None

    def get_instance(self, name: str) -> Optional[PluginWidget]:
        """Get an existing plugin instance."""
        return self._instances.get(name)

    def list_plugins(self) -> List[PluginInfo]:
        """Get list of all registered plugins."""
        return [cls.PLUGIN_INFO for cls in self._plugins.values() if cls.PLUGIN_INFO]

    def list_commands(self) -> List[PluginCommand]:
        """Get all commands from all instantiated plugins."""
        commands = []
        for instance in self._instances.values():
            commands.extend(instance.commands)
        return commands


_registry = PluginRegistry()


def get_plugin_registry() -> PluginRegistry:
    """Get the global plugin registry."""
    return _registry


def register_plugin(name: str | None = None, **kwargs):
    """
    Decorator to register a plugin class.

    Args:
        name: Optional plugin name (defaults to class name)

    Example:
        ```python
        @register_plugin("my-plugin")
        class MyPlugin(PluginWidget):
            pass
        ```
    """

    def decorator(cls: Type[PluginWidget]) -> Type[PluginWidget]:
        """Decorator factory for plugin registration."""
        if cls.PLUGIN_INFO is None:
            cls.PLUGIN_INFO = PluginInfo(name=name or cls.__name__, **kwargs)
        elif name:
            cls.PLUGIN_INFO.name = name

        _registry.register(cls)
        return cls

    return decorator


class PluginContainer(Vertical):
    """
    Container for plugin widgets with error boundary.

    Wraps plugin widgets to catch errors and display fallback UI.
    """

    DEFAULT_CSS = """
    PluginContainer {
        width: 100%;
        height: auto;
    }

    PluginContainer.error {
        background: $error 10%;
        border: solid $error;
        padding: 1;
    }
    """

    def __init__(self, plugin: PluginWidget, **kwargs):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self.plugin = plugin
        self._error: Optional[Exception] = None

    def compose(self) -> ComposeResult:
        """Compose with error boundary."""
        from textual.widgets import Static

        if self._error:
            yield Static(f"⚠️ Plugin error: {self._error}")
        else:
            try:
                yield self.plugin
            except Exception as e:
                self._error = e
                logger.error(f"Plugin {self.plugin.plugin_id} error: {e}")
                yield Static(f"⚠️ Plugin error: {e}")


def create_plugin_widget(plugin_name: str, **kwargs) -> Optional[PluginContainer]:
    """
    Create a plugin widget wrapped in error boundary.

    Args:
        plugin_name: Name of registered plugin
        **kwargs: Arguments for plugin constructor

    Returns:
        PluginContainer with plugin instance
    """
    instance = _registry.instantiate(plugin_name, **kwargs)
    if instance:
        return PluginContainer(instance)
    return None


@register_plugin(
    "sample",
    version="1.0.0",
    description="Sample plugin demonstrating SDK features",
    author="Aura Team",
)
class SamplePlugin(PluginWidget):
    """Sample plugin for demonstration."""

    DEFAULT_CSS = """
    SamplePlugin {
        border: solid $primary;
        padding: 1;
        margin: 1;
    }
    """

    message: reactive[str] = reactive("Hello from SamplePlugin!")

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        from textual.widgets import Button, Static

        yield Static(self.message, id="message")
        yield Button("Click me!", id="click-btn")

    def on_plugin_mount(self) -> None:
        """Handle plugin mount lifecycle event."""
        self.log.info(f"SamplePlugin mounted with id: {self.plugin_id}")

    def on_button_pressed(self, event) -> None:
        """Handle button press events."""
        if event.button.id == "click-btn":
            self.greet()

    @plugin_command("greet", "Show greeting message", keybind="ctrl+shift+g")
    def greet(self) -> None:
        """Greet command."""
        self.show_toast("Greetings from SamplePlugin! 🎉")
        self.emit_event("greeted", {"time": "now"})

    @on_event("tui.theme.changed")
    def on_theme_changed(self, payload: Dict[str, Any]) -> None:
        """Handle theme change event."""
        self.log.info(f"Theme changed to: {payload.get('theme_name')}")


__all__ = [
    "PluginCommand",
    "PluginContainer",
    "PluginInfo",
    "PluginRegistry",
    "PluginWidget",
    "create_plugin_widget",
    "get_plugin_registry",
    "on_event",
    "plugin_command",
    "register_plugin",
]
