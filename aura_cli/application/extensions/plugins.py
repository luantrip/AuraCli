"""Canonical plugin contracts and coordination use cases."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import threading
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class PluginHook(Enum):
    ON_STARTUP = "on_startup"
    ON_SHUTDOWN = "on_shutdown"
    ON_SESSION_START = "on_session_start"
    ON_SESSION_END = "on_session_end"
    BEFORE_COMMAND = "before_command"
    AFTER_COMMAND = "after_command"
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    BEFORE_LLM_CALL = "before_llm_call"
    AFTER_LLM_CALL = "after_llm_call"
    ON_AGENT_START = "on_agent_start"
    ON_AGENT_END = "on_agent_end"
    ON_AGENT_ERROR = "on_agent_error"
    ON_ERROR = "on_error"
    ON_RENDER = "on_render"


@dataclass
class PluginContext:
    hook: PluginHook
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: dict[str, Any] = field(default_factory=dict)
    cancelled: bool = False

    def cancel(self) -> None:
        self.cancelled = True

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value


@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str = ""
    author: str = ""
    license: str = ""
    homepage: str = ""
    dependencies: list[str] = field(default_factory=list)
    min_aura_version: str = ""


@dataclass(frozen=True)
class PluginToolDescriptor:
    function: Callable[..., Any]
    effect: str
    risk: str
    description: str = ""
    schema: dict[str, Any] = field(default_factory=dict)


class AuraPlugin(ABC):
    """Host-neutral base contract implemented by Aura plugins."""

    def __init__(self) -> None:
        self._enabled = True
        self._context: dict[str, Any] = {}

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def version(self) -> str: ...

    @property
    def description(self) -> str:
        return ""

    @property
    def author(self) -> str:
        return ""

    @property
    def dependencies(self) -> list[str]:
        return []

    @property
    def hooks(self) -> dict[PluginHook, Callable[[PluginContext], None]]:
        return {}

    def get_tools(self) -> dict[str, PluginToolDescriptor]:
        return {}

    def get_commands(self) -> dict[str, Callable[..., Any]]:
        return {}

    def get_ui_components(self) -> dict[str, Any]:
        return {}

    def initialize(self, context: dict[str, Any]) -> None:
        self._context = context

    def shutdown(self) -> None:
        """Release plugin-owned resources."""
        return None

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def get_metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name=self.name,
            version=self.version,
            description=self.description,
            author=self.author,
            dependencies=self.dependencies,
        )


PluginToolRegistrar = Callable[[AuraPlugin], bool]


class PluginCoordinator:
    """Coordinate plugin lifecycle, dependencies, commands and hook emission."""

    def __init__(
        self,
        *,
        tool_registrar: Optional[PluginToolRegistrar] = None,
    ) -> None:
        self.plugins: dict[str, AuraPlugin] = {}
        self.hooks: dict[PluginHook, list[Callable[..., Any]]] = {
            hook: [] for hook in PluginHook
        }
        self.lock = threading.RLock()
        self._context: dict[str, Any] = {}
        self._tool_registrar = tool_registrar

    def set_context(self, context: dict[str, Any]) -> None:
        self._context = context

    def register_plugin(self, plugin: AuraPlugin) -> bool:
        with self.lock:
            if plugin.name in self.plugins:
                return False
            if any(
                dependency not in self.plugins for dependency in plugin.dependencies
            ):
                return False
            try:
                plugin.initialize(self._context)
                if self._tool_registrar is not None and not self._tool_registrar(
                    plugin
                ):
                    plugin.shutdown()
                    return False
            except Exception as exc:
                logger.error("Plugin %s initialization failed: %s", plugin.name, exc)
                return False
            for hook, callback in plugin.hooks.items():
                self.hooks[hook].append(callback)
            commands = self._context.setdefault("plugin_commands", {})
            for name, handler in plugin.get_commands().items():
                commands[name] = {
                    "plugin": plugin.name,
                    "handler": handler,
                    "description": handler.__doc__ or f"Command from {plugin.name}",
                }
            self.plugins[plugin.name] = plugin
            return True

    def unregister_plugin(self, plugin_name: str) -> bool:
        with self.lock:
            plugin = self.plugins.get(plugin_name)
            if plugin is None:
                return False
            for hook, callback in plugin.hooks.items():
                if callback in self.hooks[hook]:
                    self.hooks[hook].remove(callback)
            try:
                plugin.shutdown()
            except Exception as exc:
                logger.warning("Plugin %s shutdown failed: %s", plugin_name, exc)
            del self.plugins[plugin_name]
            return True

    def emit_hook(self, hook: PluginHook, **kwargs: Any) -> list[Any]:
        context = PluginContext(hook=hook, data=kwargs)
        results: list[Any] = []
        with self.lock:
            for callback in self.hooks[hook]:
                try:
                    results.append(callback(context))
                except Exception as exc:
                    logger.error("Plugin hook %s failed: %s", hook.value, exc)
                if context.cancelled:
                    break
        return results

    def get_plugin(self, name: str) -> Optional[AuraPlugin]:
        return self.plugins.get(name)

    def list_plugins(self) -> list[PluginMetadata]:
        return [plugin.get_metadata() for plugin in self.plugins.values()]

    def is_plugin_enabled(self, name: str) -> bool:
        plugin = self.plugins.get(name)
        return plugin.is_enabled if plugin is not None else False

    def enable_plugin(self, name: str) -> bool:
        plugin = self.plugins.get(name)
        if plugin is None:
            return False
        plugin.enable()
        return True

    def disable_plugin(self, name: str) -> bool:
        plugin = self.plugins.get(name)
        if plugin is None:
            return False
        plugin.disable()
        return True

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_plugins": len(self.plugins),
            "enabled_plugins": sum(
                1 for plugin in self.plugins.values() if plugin.is_enabled
            ),
            "total_hooks": sum(len(callbacks) for callbacks in self.hooks.values()),
            "plugins": [
                {
                    "name": plugin.name,
                    "version": plugin.version,
                    "enabled": plugin.is_enabled,
                    "tools": len(plugin.get_tools()),
                    "commands": len(plugin.get_commands()),
                    "hooks": len(plugin.hooks),
                }
                for plugin in self.plugins.values()
            ],
        }
