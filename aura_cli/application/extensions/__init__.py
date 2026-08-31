"""Extension registry and lifecycle contracts."""

from .hooks import ExtensionHook, ExtensionHookManager, HookType
from .lifecycle import ExtensionLifecycle, LifecycleEvent, LifecycleHandler
from .plugins import (
    AuraPlugin,
    PluginContext,
    PluginCoordinator,
    PluginHook,
    PluginMetadata,
    PluginToolDescriptor,
)
from .registry import ExtensionInfo, ExtensionRegistry, ExtensionStatus
from .subprocess_hooks import (
    CommandHook,
    HookEvent,
    HookResult,
    hook_cache_key,
    hook_matches,
)

__all__ = [
    "AuraPlugin",
    "CommandHook",
    "ExtensionHook",
    "ExtensionHookManager",
    "ExtensionInfo",
    "ExtensionLifecycle",
    "ExtensionRegistry",
    "ExtensionStatus",
    "HookEvent",
    "HookResult",
    "HookType",
    "LifecycleEvent",
    "LifecycleHandler",
    "PluginContext",
    "PluginCoordinator",
    "PluginHook",
    "PluginMetadata",
    "PluginToolDescriptor",
    "hook_cache_key",
    "hook_matches",
]
