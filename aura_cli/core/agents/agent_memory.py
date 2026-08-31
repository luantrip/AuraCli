"""Persistent cross-session memory for Aura CLI agents.

AgentMemory stores MemoryEntry records on disk (JSON) keyed by agent+key,
with optional TTL, access tracking and automatic expiry cleanup. Allows
agents to remember context, decisions and results between sessions.
"""

from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class MemoryEntry:
    """A single agent memory entry (id, content, type, importance, timestamps)."""

    id: str
    agent_id: str
    key: str
    value: Any
    context: Dict[str, Any]
    timestamp: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    ttl: Optional[int] = None

    def is_expired(self) -> bool:
        """Return True if the memory entry has expired."""
        if self.ttl is None:
            return False

        age = (datetime.now() - self.timestamp).total_seconds()
        return age > self.ttl

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        if self.last_accessed:
            data["last_accessed"] = self.last_accessed.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        """Create an instance from a dictionary."""
        data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        if data.get("last_accessed"):
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        return cls(**data)


class AgentMemory:
    """Memory system with semantic search and disk persistence for agents."""

    def __init__(
        self, storage_path: Optional[str] = None, max_memories_per_agent: int = 1000
    ):
        """Initialise agent memory.

        Args:
            agent_id: Unique agent identifier.
            persist: Whether to persist memories to disk."""
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            from aura_cli.core.paths import get_aura_home

            aura_dir = get_aura_home()
            self.storage_path = aura_dir / "memory"

        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.max_memories_per_agent = max_memories_per_agent

        self.memories: Dict[str, Dict[str, MemoryEntry]] = defaultdict(dict)

        self.stats = get_stats()
        self.total_stored = 0
        self.total_retrieved = 0
        self.total_expired = 0

        self._load_persistent_memories()

        logger.info(
            f"AgentMemory initialized (storage: {self.storage_path}, "
            f"memories loaded: {sum(len(m) for m in self.memories.values())})"
        )

    def store(
        self,
        agent_id: str,
        key: str,
        value: Any,
        context: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> str:
        """Store a new memory entry and return its ID."""
        import uuid

        memory_id = str(uuid.uuid4())[:8]

        entry = MemoryEntry(
            id=memory_id,
            agent_id=agent_id,
            key=key,
            value=value,
            context=context or {},
            timestamp=datetime.now(),
            ttl=ttl,
        )

        self.memories[agent_id][memory_id] = entry

        if len(self.memories[agent_id]) > self.max_memories_per_agent:
            sorted_entries = sorted(
                self.memories[agent_id].values(), key=lambda e: e.timestamp
            )
            for old_entry in sorted_entries[
                : len(sorted_entries) - self.max_memories_per_agent
            ]:
                del self.memories[agent_id][old_entry.id]

        self._save_agent_memories(agent_id)

        self.total_stored += 1
        self.stats.track_tool_usage("agent_memory_store")

        logger.debug(f"Memória {memory_id} armazenada para agente {agent_id}: {key}")

        return memory_id

    def retrieve(
        self,
        agent_id: str,
        key: Optional[str] = None,
        context_filter: Optional[Dict[str, Any]] = None,
        limit: int = 10,
    ) -> List[MemoryEntry]:
        """Retrieve memories by semantic query, sorted by relevance."""
        if agent_id not in self.memories:
            return []

        self._cleanup_expired(agent_id)

        entries = list(self.memories[agent_id].values())

        if key:
            entries = [e for e in entries if e.key == key]

        if context_filter:
            filtered = []
            for entry in entries:
                match = True
                for k, v in context_filter.items():
                    if entry.context.get(k) != v:
                        match = False
                        break
                if match:
                    filtered.append(entry)
            entries = filtered

        entries.sort(key=lambda e: e.last_accessed or e.timestamp, reverse=True)

        for entry in entries[:limit]:
            entry.access_count += 1
            entry.last_accessed = datetime.now()

        results = entries[:limit]

        self.total_retrieved += len(results)
        self.stats.track_tool_usage("agent_memory_retrieve")

        logger.debug(f"Recuperadas {len(results)} memórias para agente {agent_id}")

        return results

    def get(self, agent_id: str, key: str, default: Any = None) -> Optional[Any]:
        """Return a specific memory by ID, or None if not found."""
        entries = self.retrieve(agent_id, key=key, limit=1)
        if entries:
            return entries[0].value
        return default

    def delete(
        self, agent_id: str, memory_id: Optional[str] = None, key: Optional[str] = None
    ) -> bool:
        """Remove a memory by ID. Returns True if found and deleted."""
        if agent_id not in self.memories:
            return False

        if memory_id:
            if memory_id in self.memories[agent_id]:
                del self.memories[agent_id][memory_id]
                self._save_agent_memories(agent_id)
                return True
        elif key:
            to_remove = [
                mid
                for mid, entry in self.memories[agent_id].items()
                if entry.key == key
            ]
            for mid in to_remove:
                del self.memories[agent_id][mid]
            if to_remove:
                self._save_agent_memories(agent_id)
                return True

        return False

    def clear_agent_memories(self, agent_id: str) -> None:
        """Clear all memories for an agent."""
        if agent_id in self.memories:
            self.memories[agent_id].clear()
            self._save_agent_memories(agent_id)
            logger.info(f"Memórias do agente {agent_id} limpas")

    def _cleanup_expired(self, agent_id: str) -> None:
        """Remove expired memories for an agent."""
        if agent_id not in self.memories:
            return

        expired = [
            mid for mid, entry in self.memories[agent_id].items() if entry.is_expired()
        ]

        for mid in expired:
            del self.memories[agent_id][mid]
            self.total_expired += 1

        if expired:
            self._save_agent_memories(agent_id)
            logger.debug(
                f"Removidas {len(expired)} memórias expiradas do agente {agent_id}"
            )

    def _save_agent_memories(self, agent_id: str) -> None:
        """Persist long-term memories to disk."""
        if agent_id not in self.memories:
            return

        self._cleanup_expired(agent_id)

        data = {
            "agent_id": agent_id,
            "memories": [entry.to_dict() for entry in self.memories[agent_id].values()],
        }

        file_path = self.storage_path / f"{agent_id}.json"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(
                f"Error saving memories for agent {agent_id}: {e}", exc_info=True
            )

    def _load_persistent_memories(self) -> None:
        """Load persistent memories from disk."""
        if not self.storage_path.exists():
            return

        loaded_count = 0
        for file_path in self.storage_path.glob("*.json"):
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                agent_id = data.get("agent_id")
                if not agent_id:
                    continue

                for mem_data in data.get("memories", []):
                    try:
                        entry = MemoryEntry.from_dict(mem_data)
                        if not entry.is_expired():
                            self.memories[agent_id][entry.id] = entry
                            loaded_count += 1
                    except Exception as e:
                        logger.warning(f"Error loading memory entry: {e}", exc_info=True)

            except Exception as e:
                logger.warning(
                    f"Error loading file {file_path}: {e}", exc_info=True
                )

        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} persistent memories")

    def get_statistics(self) -> Dict[str, Any]:
        """Return memory usage statistics as a dict."""
        total_memories = sum(len(m) for m in self.memories.values())

        return {
            "total_agents": len(self.memories),
            "total_memories": total_memories,
            "total_stored": self.total_stored,
            "total_retrieved": self.total_retrieved,
            "total_expired": self.total_expired,
            "storage_path": str(self.storage_path),
        }

    def __repr__(self) -> str:
        """Return a string representation of the memory system."""
        total = sum(len(m) for m in self.memories.values())
        return f"<AgentMemory(agents={len(self.memories)}, memories={total})>"
