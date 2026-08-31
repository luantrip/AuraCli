"""Core TUI Systems for Aura CLI.

Foundational systems providing event management, state synchronization,
error handling, and caching.

Systems:
- Event Bus: Typed event system with Pydantic validation
- Sync Manager: Reactive state synchronization with batching
- Sync Store: Centralized state store with path-based access
- Error Handler: Global error handling with recovery
- Cache Manager: Persistent settings storage

Exports:
- TUIEventBus, TUIEvents, EventDefinition
- SyncManager, SyncStore
- TUIErrorHandler
- CacheManager, get_cache_manager
"""

from aura_cli.tui.core.cache_manager import CacheManager, get_cache_manager
from aura_cli.tui.core.error_handler import TUIErrorHandler
from aura_cli.tui.core.event_bus import EventDefinition, TUIEventBus, TUIEvents
from aura_cli.tui.core.sync_manager import SyncManager
from aura_cli.tui.core.sync_store import SyncStore

__all__ = [
    "CacheManager",
    "EventDefinition",
    "SyncManager",
    "SyncStore",
    "TUIErrorHandler",
    "TUIEventBus",
    "TUIEvents",
    "get_cache_manager",
]
