"""Core adapter for canonical application plugin contracts."""

from __future__ import annotations

import logging
from typing import Optional

from aura_cli.application.extensions.plugins import (
    AuraPlugin,
    PluginContext,
    PluginCoordinator,
    PluginHook,
    PluginMetadata,
    PluginToolDescriptor,
)

logger = logging.getLogger(__name__)


class PluginManager(PluginCoordinator):
    """Application plugin coordinator wired to Core's guarded tool registry."""

    def __init__(self) -> None:
        super().__init__(tool_registrar=self._register_tools)

    @staticmethod
    def _register_tools(plugin: AuraPlugin) -> bool:
        try:
            from aura_cli.core.service_registry import (
                ToolCategory,
                ToolEffect,
                ToolRisk,
                get_service_registry,
            )

            tools = plugin.get_tools()
            invalid = [
                name
                for name, descriptor in tools.items()
                if not isinstance(descriptor, PluginToolDescriptor)
            ]
            if invalid:
                raise ValueError(
                    "Plugin tools require PluginToolDescriptor with explicit risk: "
                    + ", ".join(sorted(invalid))
                )
            registry = get_service_registry()
            for tool_name, descriptor in tools.items():
                description = (
                    descriptor.description
                    or descriptor.function.__doc__
                    or f"Tool from plugin {plugin.name}"
                )
                registry.register_tool(
                    f"{plugin.name}_{tool_name}",
                    ToolCategory.DEVELOPMENT,
                    description.split("\n")[0],
                    descriptor.function,
                    descriptor.schema,
                    effect=ToolEffect(descriptor.effect),
                    risk=ToolRisk(descriptor.risk),
                )
            return True
        except Exception as exc:
            logger.error("Plugin %s tool registration failed: %s", plugin.name, exc)
            return False


_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def aura_tool(name: Optional[str] = None, description: Optional[str] = None):
    """Mark a callable as an Aura tool candidate."""

    def decorator(func):
        func._aura_tool = True
        func._aura_tool_name = name or func.__name__
        func._aura_tool_description = description or func.__doc__ or ""
        return func

    return decorator


def aura_command(name: Optional[str] = None, description: Optional[str] = None):
    """Mark a callable as an Aura slash command candidate."""

    def decorator(func):
        func._aura_command = True
        func._aura_command_name = name or f"/{func.__name__}"
        func._aura_command_description = description or func.__doc__ or ""
        return func

    return decorator


def aura_hook(hook: PluginHook):
    """Mark a callable as a handler for a canonical plugin hook."""

    def decorator(func):
        func._aura_hook = hook
        return func

    return decorator


__all__ = [
    "AuraPlugin",
    "PluginContext",
    "PluginHook",
    "PluginManager",
    "PluginMetadata",
    "PluginToolDescriptor",
    "aura_command",
    "aura_hook",
    "aura_tool",
    "get_plugin_manager",
]
