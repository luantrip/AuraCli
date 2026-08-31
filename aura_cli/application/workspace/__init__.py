"""Workspace-scoped application state."""

from .checkpoint_coordinator import WorkerCheckpointCoordinator
from .consolidation import (
    ConsolidatedRule,
    ConsolidationOutcome,
    ConsolidationStatus,
    consolidate_notebook_rules,
)
from .context_usage import get_context_percentage, should_compact_context
from .conversation import ChatMessage, ConversationMemory
from .memory_sync import (
    MemorySynchronizer,
    UnifiedMemoryResult,
    get_memory_synchronizer,
)
from .state import WorkspaceState
from .tangent import ConversationCheckpoint, TangentManager, TangentState

__all__ = [
    "ChatMessage",
    "ConsolidatedRule",
    "ConsolidationOutcome",
    "ConsolidationStatus",
    "ConversationCheckpoint",
    "ConversationMemory",
    "MemorySynchronizer",
    "TangentManager",
    "TangentState",
    "UnifiedMemoryResult",
    "WorkerCheckpointCoordinator",
    "WorkspaceState",
    "consolidate_notebook_rules",
    "get_context_percentage",
    "get_memory_synchronizer",
    "should_compact_context",
]
