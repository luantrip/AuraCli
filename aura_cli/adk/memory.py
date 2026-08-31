"""
ADK Memory System.

ADK-specific memory backed by host runtime ports:
- MemoryEntry, Memory (ABC), VectorMemory, PersistentMemory, ConversationMemory
- MemoryStore: deprecated alias for PersistentMemory (until ADK 1.0)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from dataclasses import dataclass, field
import hashlib
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from aura_cli.application.agents import get_agent_runtime
from aura_cli.application.workspace.conversation import (
    ConversationMemory as ApplicationConversationMemory,
)

logger = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """A single entry in memory."""

    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    embedding: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryEntry:
        """Deserialize from dictionary."""
        return cls(
            id=data["id"],
            content=data["content"],
            metadata=data.get("metadata", {}),
            timestamp=data.get("timestamp", time.time()),
        )


class Memory(ABC):
    """Abstract base class for ADK memory implementations."""

    @abstractmethod
    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add content to memory, returns entry ID."""

    @abstractmethod
    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get entry by ID."""

    @abstractmethod
    async def search(self, query: str, limit: int = 10, **filters) -> List[MemoryEntry]:
        """Search memory for relevant entries."""

    @abstractmethod
    async def delete(self, entry_id: str) -> bool:
        """Delete entry by ID."""

    @abstractmethod
    async def clear(self) -> None:
        """Clear all entries."""

    @abstractmethod
    async def size(self) -> int:
        """Get number of entries."""


class VectorMemory(Memory):
    """
    Async vector memory using core.memory VectorStore.

    This wraps the synchronous VectorStore to provide an async interface
    for ADK agents. Uses ChromaDB (preferred) or FAISS under the hood.
    """

    def __init__(
        self,
        collection_name: str = "adk_memory",
        persist_path: Optional[str] = None,
    ):
        """
        Initialize VectorMemory.

        Args:
            collection_name: Name for the vector collection
            persist_path: Path for persistent storage
        """
        self._store: Optional[Any] = None
        self._collection_name = collection_name
        self._persist_path = persist_path
        self._initialized = False

    def _ensure_initialized(self) -> Any:
        """Lazy initialization of vector store."""
        if self._store is None:
            factory = get_agent_runtime().create_vector_store
            if factory is None:
                raise RuntimeError("Vector store factory is not configured")
            self._store = factory(
                self._collection_name,
                self._persist_path,
            )
            self._initialized = True
            logger.debug(
                f"VectorMemory initialized with backend: {self._store.backend_name}"
            )
        return self._store

    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add content with vector embedding."""
        store = self._ensure_initialized()
        loop = asyncio.get_running_loop()
        doc_id = await loop.run_in_executor(None, lambda: store.add(content, metadata))
        return doc_id

    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get entry by ID."""
        store = self._ensure_initialized()
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(None, lambda: store.get(entry_id))

        if result:
            return MemoryEntry(
                id=result.id,
                content=result.content,
                metadata=result.metadata,
            )
        return None

    async def search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.5,
        **filters,
    ) -> List[MemoryEntry]:
        """Search using vector similarity."""
        store = self._ensure_initialized()
        loop = asyncio.get_running_loop()
        results = await loop.run_in_executor(
            None, lambda: store.search(query, limit, filters.get("filter_metadata"))
        )

        return [
            MemoryEntry(
                id=r.id,
                content=r.content,
                metadata=r.metadata,
            )
            for r in results
            if r.score >= threshold
        ]

    async def delete(self, entry_id: str) -> bool:
        """Delete entry by ID."""
        store = self._ensure_initialized()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, lambda: store.delete(entry_id))

    async def clear(self) -> None:
        """Clear all entries."""
        store = self._ensure_initialized()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, store.clear)

    async def size(self) -> int:
        """Get entry count."""
        store = self._ensure_initialized()
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, store.count)


class PersistentMemory(Memory):
    """
    File-based persistent memory using JSON Lines format.

    Features:
        - Append-only writes for performance
        - Lazy loading on first access
        - Simple keyword search
    """

    def __init__(self, path: Path):
        """
        Initialize PersistentMemory.

        Args:
            path: Path to .jsonl storage file
        """
        self._path = Path(path)
        self._store: Dict[str, MemoryEntry] = {}
        self._is_loaded = False
        self._lock = asyncio.Lock()

    async def _load(self) -> None:
        """Load from JSONL file."""
        async with self._lock:
            if self._is_loaded:
                return
            try:
                if self._path.exists():
                    with self._path.open("r", encoding="utf-8") as f:
                        for line in f:
                            if line.strip():
                                data = json.loads(line)
                                entry = MemoryEntry.from_dict(data)
                                self._store[entry.id] = entry
                self._is_loaded = True
            except Exception as e:
                logger.error(f"Failed to load memory from {self._path}: {e}")
                self._is_loaded = True

    async def _append_to_file(self, entry: MemoryEntry) -> None:
        """Append entry to file."""
        async with self._lock:
            try:
                self._path.parent.mkdir(parents=True, exist_ok=True)

                def _write():
                    with self._path.open("a", encoding="utf-8") as f:
                        f.write(json.dumps(entry.to_dict()) + "\n")

                await asyncio.to_thread(_write)
            except Exception as e:
                logger.error(f"Failed to append to {self._path}: {e}")

    async def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add entry and persist."""
        await self._load()
        entry_id = hashlib.sha256(f"{content}{time.time()}".encode()).hexdigest()[:16]
        entry = MemoryEntry(id=entry_id, content=content, metadata=metadata or {})

        async with self._lock:
            self._store[entry_id] = entry

        await self._append_to_file(entry)
        return entry_id

    async def get(self, entry_id: str) -> Optional[MemoryEntry]:
        """Get entry by ID."""
        await self._load()
        return self._store.get(entry_id)

    async def search(self, query: str, limit: int = 10, **filters) -> List[MemoryEntry]:
        """Search by substring."""
        await self._load()
        query_lower = query.lower()
        results = [
            entry
            for entry in self._store.values()
            if query_lower in entry.content.lower()
        ]
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results[:limit]

    async def delete(self, entry_id: str) -> bool:
        """Delete entry and rewrite file."""
        await self._load()
        async with self._lock:
            if entry_id in self._store:
                del self._store[entry_id]
                self._rewrite_file()
                return True
        return False

    async def clear(self) -> None:
        """Clear all entries."""
        async with self._lock:
            self._store.clear()
            if self._path.exists():
                self._path.unlink()
            self._is_loaded = True

    async def size(self) -> int:
        """Get entry count."""
        await self._load()
        return len(self._store)

    def _rewrite_file(self) -> None:
        """Rewrite file after deletion."""
        try:
            with self._path.open("w", encoding="utf-8") as f:
                for entry in self._store.values():
                    f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception as e:
            logger.error(f"Failed to rewrite {self._path}: {e}")


class ConversationMemory(ApplicationConversationMemory):
    """
    ADK-compatible conversation memory.

    Compatibility subtype of the canonical application conversation model.
    """


MemoryStore = PersistentMemory


def get_default_memory_path() -> Path:
    """Get default path for memory storage."""
    from aura_cli.application.artifacts import ArtifactLayout

    return ArtifactLayout().user("adk", "memory")


def create_memory(
    memory_type: str = "vector",
    collection_name: str = "adk_memory",
    **kwargs,
) -> Memory:
    """
    Factory function to create memory instances.

    Args:
        memory_type: Type of memory (vector, persistent, conversation)
        collection_name: Name for vector collection
        **kwargs: Additional arguments

    Returns:
        Memory instance
    """
    if memory_type == "vector":
        return VectorMemory(
            collection_name=collection_name,
            persist_path=kwargs.get("persist_path"),
        )
    elif memory_type == "persistent":
        path = kwargs.get("path", get_default_memory_path() / "default.jsonl")
        return PersistentMemory(Path(path))
    else:
        return VectorMemory(collection_name=collection_name)


__all__ = [
    "ConversationMemory",
    "Memory",
    "MemoryEntry",
    "MemoryStore",
    "PersistentMemory",
    "VectorMemory",
    "create_memory",
    "get_default_memory_path",
]
