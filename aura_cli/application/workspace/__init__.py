"""Workspace-scoped application state."""

from .checkpoint_coordinator import WorkerCheckpointCoordinator
from .consolidation import (
    ConsolidatedRule,
    ConsolidationOutcome,
    ConsolidationStatus,
    consolidate_notebook_rules,
)
from .context_usage import (
    DEFAULT_CONTEXT_WINDOW,
    MIN_CONTEXT_HARD_LIMIT,
    context_hard_limit_for_model,
    context_window_for_model,
    get_context_percentage,
    should_compact_context,
)
from .conversation import ChatMessage, ConversationMemory
from .memory_sync import (
    MemorySynchronizer,
    UnifiedMemoryResult,
    get_memory_synchronizer,
)
from .state import WorkspaceState
from .tangent import ConversationCheckpoint, TangentManager, TangentState

__all__ = [
    "DEFAULT_CONTEXT_WINDOW",
    "MIN_CONTEXT_HARD_LIMIT",
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
    "context_hard_limit_for_model",
    "context_window_for_model",
    "get_context_percentage",
    "get_memory_synchronizer",
    "should_compact_context",
]
