"""Enhanced Plugin Manager for Aura TUI.

Provides comprehensive plugin system with dynamic loading and lifecycle management.

Features:
- Dynamic module discovery and loading with importlib
- Well-defined plugin interface (AuraTUIPluginBase)
- Widget hosting and registration
- Plugin lifecycle management (load/unload/enable/disable)
- Command and keybinding extension
- Configuration support
- Error handling and reporting

Plugin Types:
- Full plugins: Inherit from AuraTUIPluginBase
- Simple widgets: Inherit from AuraTUIPluginWidget
"""

from abc import ABC, abstractmethod
import contextlib
import importlib.util
from pathlib import Path
import sys
from typing import Any, Callable, Dict, List, Optional, Type

from textual.widget import Widget

from aura_cli.application.extensions import AuraPlugin, PluginMetadata


class AuraTUIPluginBase(AuraPlugin, ABC):
    """Base class for Aura TUI plugins.

    All full-featured plugins must inherit from this class and implement
    the required abstract methods. Provides lifecycle hooks and extension
    points for widgets, commands, and keybindings.

    Attributes:
        PLUGIN_NAME: Plugin display name
        PLUGIN_VERSION: Plugin version string
        PLUGIN_AUTHOR: Plugin author
        PLUGIN_DESCRIPTION: Plugin description
    """

    PLUGIN_NAME: str = "Unnamed Plugin"
    PLUGIN_VERSION: str = "1.0.0"
    PLUGIN_AUTHOR: str = "Unknown"
    PLUGIN_DESCRIPTION: str = ""

    def __init__(self, app=None):
        """Initialize plugin with app reference.

        Args:
            app: Reference to main AuraTUI application
        """
        super().__init__()
        self.app = app

    @property
    def name(self) -> str:
        return self.PLUGIN_NAME

    @property
    def version(self) -> str:
        return self.PLUGIN_VERSION

    @property
    def author(self) -> str:
        return self.PLUGIN_AUTHOR

    @property
    def description(self) -> str:
        return self.PLUGIN_DESCRIPTION

    @property
    def metadata(self) -> PluginMetadata:
        """Get plugin metadata.

        Returns:
            PluginMetadata instance
        """
        return self.get_metadata()

    def get_ui_components(self) -> Dict[str, Type[Widget]]:
        return self.get_widgets()

    def initialize(self, context: dict[str, Any]) -> None:
        super().initialize(context)
        self.app = context.get("app", self.app)
        self.on_load()

    def shutdown(self) -> None:
        self.on_unload()

    @abstractmethod
    def get_widgets(self) -> Dict[str, Type[Widget]]:
        """Return widgets provided by this plugin.

        Returns:
            Dictionary mapping widget names to Widget classes
        """

    @abstractmethod
    def on_load(self) -> None:
        """Lifecycle hook called when plugin is loaded.

        Override in subclass to perform initialization tasks.
        """

    @abstractmethod
    def on_unload(self) -> None:
        """Lifecycle hook called when plugin is unloaded.

        Override in subclass to perform cleanup tasks.
        """

    @abstractmethod
    def on_app_ready(self) -> None:
        """Lifecycle hook called when TUI app is fully mounted.

        Override in subclass to perform post-mount initialization.
        """

    def get_keybindings(self) -> List[tuple]:
        """Return additional keybindings provided by plugin.

        Returns:
            List of (key, action, description) tuples
        """
        return []

    def get_commands(self) -> Dict[str, Callable]:
        """Return additional commands provided by plugin.

        Returns:
            Dictionary mapping command names to handler functions
        """
        return {}

    @property
    def enabled(self) -> bool:
        """Check if plugin is enabled.

        Returns:
            True if plugin is enabled
        """
        return self.is_enabled

    @enabled.setter
    def enabled(self, value: bool):
        """Set plugin enabled state.

        Args:
            value: New enabled state
        """
        self.enable() if value else self.disable()


class AuraTUIPluginWidget:
    """Simple interface for widget-only plugins.

    For simpler plugins that only provide a widget without full lifecycle
    management. Widgets can specify their preferred location in the UI.

    Attributes:
        WIDGET_CLASS: Widget class to register
        WIDGET_NAME: Widget display name
        WIDGET_LOCATION: Preferred location ("sidebar", "main", "footer", "dashboard")
        WIDGET_PRIORITY: Layout priority (lower = higher priority)
    """

    WIDGET_CLASS: Type[Widget] = None  # type: ignore[assignment]
    WIDGET_NAME: str = "Unnamed Plugin Widget"
    WIDGET_LOCATION: str = "dashboard"
    WIDGET_PRIORITY: int = 100


class PluginManager:
    """Plugin discovery, loading, and lifecycle manager.

    Manages the complete plugin lifecycle from discovery through loading,
    enabling/disabling, and unloading. Provides centralized registry for
    plugin widgets, commands, and keybindings.

    Features:
        - Automatic plugin discovery in specified directories
        - Dynamic module loading with importlib
        - Lifecycle management (load/unload/enable/disable)
        - Widget registration and location mapping
        - Command and keybinding extension
        - Error tracking and reporting
    """

    def __init__(self, plugin_dirs: Optional[List[str]] = None, app=None):
        """Initialize plugin manager.

        Args:
            plugin_dirs: List of directories to search for plugins
            app: Reference to main AuraTUI application
        """
        self.plugin_dirs = plugin_dirs or []
        self.app = app

        self.loaded_plugins: Dict[str, AuraTUIPluginBase] = {}
        self.available_widgets: Dict[str, Type[Widget]] = {}
        self.widget_locations: Dict[str, str] = {}
        self.plugin_commands: Dict[str, Callable] = {}
        self.plugin_keybindings: List[tuple] = []

        self._load_errors: List[str] = []

    def _discover_plugins(self):
        """Discover plugin modules in specified directories.

        Yields:
            Tuples of (module_name, module_path)
        """
        for plugin_dir in self.plugin_dirs:
            plugin_path = Path(plugin_dir)
            if not plugin_path.is_dir():
                continue

            for item in plugin_path.iterdir():
                if item.suffix == ".py" and item.name != "__init__.py":
                    module_name = item.stem
                    yield module_name, str(item)
                elif item.is_dir() and (item / "__init__.py").exists():
                    yield item.name, str(item / "__init__.py")

    def load_plugins(self):
        """Load all discoverable plugins with error handling."""
        self._load_errors.clear()

        for module_name, module_path in self._discover_plugins():
            try:
                self._load_plugin(module_name, module_path)
            except Exception as e:
                error_msg = f"Error loading plugin '{module_name}': {e}"
                self._load_errors.append(error_msg)
                if self.app:
                    with contextlib.suppress(Exception):
                        self.app.notify(error_msg, severity="warning")

    def _load_plugin(self, module_name: str, module_path: str):
        """Load single plugin module and register components.

        Args:
            module_name: Module name
            module_path: Path to module file
        """
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None or spec.loader is None:
            return

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        for attr_name in dir(module):
            attr = getattr(module, attr_name)

            if (
                isinstance(attr, type)
                and issubclass(attr, AuraTUIPluginBase)
                and attr is not AuraTUIPluginBase
            ):
                plugin = attr(app=self.app)
                plugin.initialize({"app": self.app})
                self.loaded_plugins[module_name] = plugin

                for widget_name, widget_class in plugin.get_widgets().items():
                    self.available_widgets[widget_name] = widget_class

                self.plugin_commands.update(plugin.get_commands())
                self.plugin_keybindings.extend(plugin.get_keybindings())

            elif (
                isinstance(attr, type)
                and issubclass(attr, AuraTUIPluginWidget)
                and attr is not AuraTUIPluginWidget
            ):
                if attr.WIDGET_CLASS is not None:
                    self.available_widgets[attr.WIDGET_NAME] = attr.WIDGET_CLASS
                    self.widget_locations[attr.WIDGET_NAME] = attr.WIDGET_LOCATION

    def unload_plugin(self, plugin_name: str):
        """Unload specific plugin and cleanup resources.

        Args:
            plugin_name: Name of plugin to unload
        """
        if plugin_name in self.loaded_plugins:
            plugin = self.loaded_plugins[plugin_name]
            plugin.shutdown()

            for widget_name in list(self.available_widgets.keys()):
                if widget_name in plugin.get_widgets():
                    del self.available_widgets[widget_name]

            for cmd_name in plugin.get_commands():
                self.plugin_commands.pop(cmd_name, None)

            del self.loaded_plugins[plugin_name]
            sys.modules.pop(plugin_name, None)

    def unload_plugins(self) -> None:
        """Unload all full plugins and clear derived registrations."""
        for plugin_name in list(self.loaded_plugins):
            try:
                self.unload_plugin(plugin_name)
            except Exception as error:
                self._load_errors.append(
                    f"Error unloading plugin '{plugin_name}': {error}"
                )
        self.available_widgets.clear()
        self.widget_locations.clear()
        self.plugin_commands.clear()
        self.plugin_keybindings.clear()

    def enable_plugin(self, plugin_name: str):
        """Enable loaded plugin.

        Args:
            plugin_name: Name of plugin to enable
        """
        if plugin_name in self.loaded_plugins:
            self.loaded_plugins[plugin_name].enable()

    def disable_plugin(self, plugin_name: str):
        """Disable plugin while keeping it loaded.

        Args:
            plugin_name: Name of plugin to disable
        """
        if plugin_name in self.loaded_plugins:
            self.loaded_plugins[plugin_name].disable()

    def notify_app_ready(self):
        """Notify all enabled plugins that app is ready."""
        for plugin in self.loaded_plugins.values():
            if plugin.is_enabled:
                try:
                    plugin.on_app_ready()
                except Exception as e:
                    self._load_errors.append(f"Plugin error on ready: {e}")

    def get_available_widgets(self) -> Dict[str, Type[Widget]]:
        """Get all available widgets from all plugins.

        Returns:
            Dictionary of widget names to Widget classes
        """
        return self.available_widgets.copy()

    def get_widgets_for_location(self, location: str) -> Dict[str, Type[Widget]]:
        """Get widgets designated for specific location.

        Args:
            location: Location identifier

        Returns:
            Dictionary of widgets for specified location
        """
        return {
            name: widget
            for name, widget in self.available_widgets.items()
            if self.widget_locations.get(name, "dashboard") == location
        }

    def get_plugin_info(self) -> List[Dict[str, Any]]:
        """Get information about all loaded plugins.

        Returns:
            List of plugin info dictionaries
        """
        info = []
        for plugin in self.loaded_plugins.values():
            meta = plugin.metadata
            info.append(
                {
                    "name": meta.name,
                    "version": meta.version,
                    "author": meta.author,
                    "description": meta.description,
                    "enabled": plugin.enabled,
                    "widgets": list(plugin.get_widgets().keys()),
                    "commands": list(plugin.get_commands().keys()),
                }
            )
        return info

    def execute_command(self, command_name: str, *args, **kwargs) -> Any:
        """Execute plugin command by name.

        Args:
            command_name: Command name to execute
            *args: Positional arguments for command
            **kwargs: Keyword arguments for command

        Returns:
            Command result

        Raises:
            ValueError: If command not found
        """
        if command_name in self.plugin_commands:
            return self.plugin_commands[command_name](*args, **kwargs)
        raise ValueError(f"Unknown plugin command: {command_name}")

    @property
    def load_errors(self) -> List[str]:
        """Get errors that occurred during plugin loading.

        Returns:
            List of error messages
        """
        return self._load_errors.copy()
