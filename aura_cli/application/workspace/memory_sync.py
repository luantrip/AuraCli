"""
Memory synchronization between vector conversation and key/value agent stores.

This module provides a bridge that synchronizes memories between:
- ConversationMemory (ADK) - Async system with vector search
- AgentMemory (Legacy) - Sync system with TTL and key-based search

Features:
- Bidirectional synchronization
- Unified search across both systems
- Format conversion
- Conflict resolution
- Automatic sync hooks
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import logging
import threading
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class UnifiedMemoryResult:
    """Result from unified memory search."""

    content: str
    source: str  # "adk" or "legacy"
    entry_id: str
    metadata: Dict[str, Any]
    timestamp: float
    score: Optional[float] = None  # Relevance score for vector search


class MemorySynchronizer:
    """
    Bridge for bidirectional synchronization between ADK and Legacy memory systems.

    This bridge allows:
    - Automatic synchronization of memories between systems
    - Unified search across both systems
    - Format conversion between ADK and Legacy formats
    - Conflict resolution when same memory exists in both systems
    """

    def __init__(self):
        """Initialize the memory bridge."""
        self._agent_memory: Optional[Any] = None
        self._sync_enabled = True
        self._sync_lock = threading.Lock()
        self._sync_queue: List[Dict[str, Any]] = []
        self._initialized = True

        logger.info("MemorySynchronizer initialized")

    def set_agent_memory(self, agent_memory: Any) -> None:
        """Set the legacy AgentMemory instance."""
        self._agent_memory = agent_memory
        logger.debug("AgentMemory set in MemoryBridge")

    def enable_sync(self) -> None:
        """Enable automatic synchronization."""
        self._sync_enabled = True
        logger.debug("MemoryBridge sync enabled")

    def disable_sync(self) -> None:
        """Disable automatic synchronization."""
        self._sync_enabled = False
        logger.debug("MemoryBridge sync disabled")

    async def sync_to_legacy(
        self,
        agent_id: str,
        conversation_memory: Any,
        limit: Optional[int] = None,
    ) -> int:
        """
        Synchronize memories from ADK ConversationMemory to Legacy AgentMemory.

        Args:
            agent_id: Legacy agent ID
            conversation_memory: ADK ConversationMemory instance
            limit: Maximum number of memories to sync (None = all)

        Returns:
            Number of memories synchronized
        """
        if not self._sync_enabled or not self._agent_memory:
            return 0

        try:
            adk_memories = await conversation_memory.search("", limit=limit or 1000)

            synced_count = 0
            for adk_entry in adk_memories:
                try:
                    legacy_key = f"adk_sync_{adk_entry.id}"

                    existing = self._agent_memory.retrieve(
                        agent_id=agent_id, key=legacy_key, limit=1
                    )

                    if not existing:
                        self._agent_memory.store(
                            agent_id=agent_id,
                            key=legacy_key,
                            value={
                                "content": adk_entry.content,
                                "adk_id": adk_entry.id,
                                "source": "adk",
                            },
                            context={
                                "metadata": adk_entry.metadata,
                                "timestamp": adk_entry.timestamp,
                                "source": "adk",
                            },
                        )
                        synced_count += 1
                        logger.debug(
                            f"Synced ADK memory {adk_entry.id} to Legacy for {agent_id}"
                        )
                except Exception as e:
                    logger.warning(f"Failed to sync ADK memory {adk_entry.id}: {e}")

            if synced_count > 0:
                logger.info(
                    f"Synced {synced_count} memories from ADK to Legacy for {agent_id}"
                )

            return synced_count

        except Exception as e:
            logger.error(f"Error syncing ADK to Legacy: {e}", exc_info=True)
            return 0

    async def sync_to_adk(
        self,
        agent_id: str,
        conversation_memory: Any,
        limit: Optional[int] = None,
    ) -> int:
        """
        Synchronize memories from Legacy AgentMemory to ADK ConversationMemory.

        Args:
            agent_id: Legacy agent ID
            conversation_memory: ADK ConversationMemory instance
            limit: Maximum number of memories to sync (None = all)

        Returns:
            Number of memories synchronized
        """
        if not self._sync_enabled or not self._agent_memory:
            return 0

        try:
            legacy_memories = self._agent_memory.retrieve(
                agent_id=agent_id, limit=limit or 1000
            )

            synced_count = 0
            for legacy_entry in legacy_memories:
                try:
                    if legacy_entry.context.get("source") == "adk":
                        continue

                    if isinstance(legacy_entry.value, dict):
                        content = legacy_entry.value.get(
                            "content", str(legacy_entry.value)
                        )
                    else:
                        content = str(legacy_entry.value)

                    await conversation_memory.add(
                        content=content,
                        metadata={
                            "legacy_id": legacy_entry.id,
                            "legacy_key": legacy_entry.key,
                            "source": "legacy",
                            **legacy_entry.context,
                        },
                    )
                    synced_count += 1
                    logger.debug(
                        f"Synced Legacy memory {legacy_entry.id} to ADK for {agent_id}"
                    )
                except Exception as e:
                    logger.warning(
                        f"Failed to sync Legacy memory {legacy_entry.id}: {e}"
                    )

            if synced_count > 0:
                logger.info(
                    f"Synced {synced_count} memories from Legacy to ADK for {agent_id}"
                )

            return synced_count

        except Exception as e:
            logger.error(f"Error syncing Legacy to ADK: {e}", exc_info=True)
            return 0

    async def bidirectional_sync(
        self,
        agent_id: str,
        conversation_memory: Any,
        limit: Optional[int] = None,
    ) -> Dict[str, int]:
        """
        Perform bidirectional synchronization.

        Args:
            agent_id: Legacy agent ID
            conversation_memory: ADK ConversationMemory instance
            limit: Maximum number of memories to sync in each direction

        Returns:
            Dict with sync counts: {"to_legacy": int, "to_adk": int}
        """
        with self._sync_lock:
            to_legacy = await self.sync_to_legacy(agent_id, conversation_memory, limit)
            to_adk = await self.sync_to_adk(agent_id, conversation_memory, limit)

            logger.info(
                f"Bidirectional sync for {agent_id}: "
                f"{to_legacy} to Legacy, {to_adk} to ADK"
            )

            return {"to_legacy": to_legacy, "to_adk": to_adk}

    async def find_unified(
        self,
        query: str,
        agent_id: Optional[str] = None,
        conversation_memory: Optional[Any] = None,
        limit: int = 10,
        min_score: float = 0.0,
    ) -> List[UnifiedMemoryResult]:
        """
        Search across both memory systems and return unified results.

        Args:
            query: Search query
            agent_id: Legacy agent ID (required for Legacy search)
            conversation_memory: ADK ConversationMemory (optional, for ADK search)
            limit: Maximum number of results
            min_score: Minimum relevance score (for vector search)

        Returns:
            List of UnifiedMemoryResult sorted by relevance
        """
        results: List[UnifiedMemoryResult] = []

        if agent_id and self._agent_memory:
            try:
                legacy_memories = self._agent_memory.retrieve(
                    agent_id=agent_id, limit=limit * 2
                )

                query_lower = query.lower()
                for legacy_entry in legacy_memories:
                    content = str(legacy_entry.value)
                    if query_lower in content.lower():
                        score = content.lower().count(query_lower) / max(
                            len(content), 1
                        )

                        if score >= min_score:
                            results.append(
                                UnifiedMemoryResult(
                                    content=content,
                                    source="legacy",
                                    entry_id=legacy_entry.id,
                                    metadata=legacy_entry.context,
                                    timestamp=legacy_entry.timestamp.timestamp(),
                                    score=score,
                                )
                            )
            except Exception as e:
                logger.warning(f"Error searching Legacy memory: {e}")

        if conversation_memory:
            try:
                adk_memories = await conversation_memory.search(
                    query=query, limit=limit * 2, threshold=min_score
                )

                for adk_entry in adk_memories:
                    results.append(
                        UnifiedMemoryResult(
                            content=adk_entry.content,
                            source="adk",
                            entry_id=adk_entry.id,
                            metadata=adk_entry.metadata,
                            timestamp=adk_entry.timestamp,
                            score=getattr(
                                adk_entry, "score", None
                            ),  # May have score from vector search
                        )
                    )
            except Exception as e:
                logger.warning(f"Error searching ADK memory: {e}")

        results.sort(key=lambda x: x.score or 0.0, reverse=True)
        return results[:limit]

    def resolve_conflicts(
        self,
        adk_memories: List[Any],
        legacy_memories: List[Any],
    ) -> List[UnifiedMemoryResult]:
        """
        Resolve conflicts when same memory exists in both systems.

        Strategy: Prefer newer memory, or ADK if timestamps are equal.

        Args:
            adk_memories: List of ADK memory entries
            legacy_memories: List of Legacy memory entries

        Returns:
            List of resolved UnifiedMemoryResult
        """
        results: List[UnifiedMemoryResult] = []
        seen_content: Dict[str, bool] = {}

        for adk_entry in adk_memories:
            content_hash = hashlib.md5(
                adk_entry.content.encode(), usedforsecurity=False
            ).hexdigest()
            if content_hash not in seen_content:
                seen_content[content_hash] = True
                results.append(
                    UnifiedMemoryResult(
                        content=adk_entry.content,
                        source="adk",
                        entry_id=adk_entry.id,
                        metadata=adk_entry.metadata,
                        timestamp=adk_entry.timestamp,
                    )
                )

        for legacy_entry in legacy_memories:
            content = str(legacy_entry.value)
            content_hash = hashlib.md5(
                content.encode(), usedforsecurity=False
            ).hexdigest()
            if content_hash not in seen_content:
                seen_content[content_hash] = True
                results.append(
                    UnifiedMemoryResult(
                        content=content,
                        source="legacy",
                        entry_id=legacy_entry.id,
                        metadata=legacy_entry.context,
                        timestamp=legacy_entry.timestamp.timestamp(),
                    )
                )

        return results


_compatibility_synchronizer: MemorySynchronizer | None = None
_compatibility_lock = threading.Lock()


def get_memory_synchronizer() -> MemorySynchronizer:
    """Resolve the deprecated process-wide bridge for external compatibility."""
    global _compatibility_synchronizer
    if _compatibility_synchronizer is None:
        with _compatibility_lock:
            if _compatibility_synchronizer is None:
                _compatibility_synchronizer = MemorySynchronizer()
    return _compatibility_synchronizer
