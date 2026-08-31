"""Core adapters and public exports for the extension system.

Lifecycle, registry and plugin contracts are defined in Application; loaders,
guarded tool registration and runtime hooks are wired here to concrete Core
services. The canonical execution hook pipeline remains in ``aura_cli.core.hooks``.
"""

from aura_cli.core.extensions.extension_loader import (
    Extension,
    ExtensionLoader,
    ExtensionMetadata,
)
from aura_cli.core.extensions.lifecycle import ExtensionLifecycle, LifecycleEvent
from aura_cli.core.extensions.plugin_api import (
    AuraPlugin,
    PluginContext,
    PluginHook,
    PluginManager,
    PluginMetadata,
    aura_command,
    aura_hook,
    aura_tool,
    get_plugin_manager,
)
from aura_cli.core.extensions.registry import ExtensionRegistry, ExtensionStatus
from aura_cli.core.hooks.extension_hooks import (
    Hook,
    HookManager,
    HookType,
)

__all__ = [
    "AuraPlugin",
    "Extension",
    "ExtensionLifecycle",
    "ExtensionLoader",
    "ExtensionMetadata",
    "ExtensionRegistry",
    "ExtensionStatus",
    "Hook",
    "HookManager",
    "HookType",
    "LifecycleEvent",
    "PluginContext",
    "PluginHook",
    "PluginManager",
    "PluginMetadata",
    "aura_command",
    "aura_hook",
    "aura_tool",
    "get_plugin_manager",
]
