"""Core-facing exports for cross-store memory synchronization."""

from aura_cli.application.workspace.memory_sync import (
    MemorySynchronizer,
    UnifiedMemoryResult,
    get_memory_synchronizer,
)

MemoryBridge = MemorySynchronizer
get_memory_bridge = get_memory_synchronizer

__all__ = ["MemoryBridge", "UnifiedMemoryResult", "get_memory_bridge"]
