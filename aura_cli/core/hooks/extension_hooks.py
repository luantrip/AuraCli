"""Core-facing exports for application extension callback hooks."""

from typing import Optional

from aura_cli.application.extensions.hooks import (
    ExtensionHook as Hook,
)
from aura_cli.application.extensions.hooks import (
    ExtensionHookManager as HookManager,
)
from aura_cli.application.extensions.hooks import (
    HookType,
)

_shared_hook_manager: Optional[HookManager] = None


def get_shared_hook_manager() -> HookManager:
    """Return the legacy process-wide callback hook manager."""
    global _shared_hook_manager
    if _shared_hook_manager is None:
        _shared_hook_manager = HookManager()
    return _shared_hook_manager


__all__ = ["Hook", "HookManager", "HookType", "get_shared_hook_manager"]
