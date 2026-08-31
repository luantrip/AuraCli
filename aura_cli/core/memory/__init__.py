"""Canonical memory package for Aura CLI — the single source of truth for memory.

Use this package for:
  - ConversationMemory  — LLM chat history with compression
  - PersistentStore     — SQLite key-value + tasks
  - VectorStore         — semantic search (ChromaDB/FAISS/keyword)
  - MemoryService       — consolidated memory interface
  - NotebookService     — disk-persisted session snapshots

For code embeddings / semantic similarity use core.memory_advanced (auxiliary).
"""

from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Dict, List, Optional

from aura_cli.application.workspace.conversation import ChatMessage, ConversationMemory
from aura_cli.core.memory import _sqlite3_fix
from aura_cli.core.memory.constitution_validator import ConstitutionValidator
from aura_cli.core.memory.memory_manager import NotebookManager
from aura_cli.core.memory.memory_service import (
    LearnedRule,
    MemoryService,
    get_memory_service,
    reset_memory_service,
)
from aura_cli.core.memory.notebook_service import NotebookService
from aura_cli.core.memory.vector_store import (
    ChromaDBVectorStore,
    FAISSVectorStore,
    KeywordVectorStore,
    SearchResult,
    VectorStore,
    create_vector_store,
    detect_best_backend,
)


class InMemoryState:
    """In-memory key-value state with change tracking.

    Note: This is the memory-layer state store. For the full session state
    (constitution, active_mode, open_files), use
    ``core.sessions.session_state.SessionState`` instead.
    """

    def __init__(self):
        """Initialize empty session state."""
        self._state: Dict[str, Any] = {}
        self._dirty: bool = False
        self._created_at = datetime.now()

    def set(self, key: str, value: Any):
        """Set a state value and mark session as dirty.

        Args:
            key: State key
            value: Value to store
        """
        self._state[key] = value
        self._dirty = True

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value by key, returning default if not found."""
        return self._state.get(key, default)

    def delete(self, key: str):
        """Remove a key from state.

        Args:
            key: State key to remove
        """
        if key in self._state:
            del self._state[key]
            self._dirty = True

    def has(self, key: str) -> bool:
        """Check if a key exists in state."""
        return key in self._state

    def all(self) -> Dict[str, Any]:
        """Return a copy of all state values."""
        return self._state.copy()

    def clear(self):
        """Clear all state and mark as dirty."""
        self._state.clear()
        self._dirty = True

    @property
    def is_dirty(self) -> bool:
        """Return True if state has unsaved changes."""
        return self._dirty

    def mark_clean(self):
        """Mark the state as clean (no unsaved changes)."""
        self._dirty = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "state": self._state,
            "created_at": self._created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InMemoryState":
        """Deserialize from dictionary."""
        session = cls()
        session._state = data.get("state", {})
        if "created_at" in data:
            session._created_at = datetime.fromisoformat(data["created_at"])
        return session


from aura_cli.core.paths import aura_path

DEFAULT_DB_PATH = str(aura_path("aura_data.db"))


class PersistentStore:
    """SQLite-backed persistent key-value and history store.

    Lazy-initialised on first use to avoid creating an empty DB in projects
    that don't need SQL persistence. Stores data as JSON-serialised values.

    Design note: NotebookService handles long-term memory (Markdown/JSON)
    for the main chat and AGI flows. PersistentStore provides structured
    SQLite storage for extensions, plugins and future SQL-query features.
    Instantiate directly where needed: ``store = PersistentStore()``.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize the instance."""
        self.db_path = Path(db_path or DEFAULT_DB_PATH).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kv_store (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    metadata TEXT,
                    timestamp REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE,
                    name TEXT,
                    status TEXT,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session
                ON conversations(session_id)
            """)

            conn.commit()

    def set(self, key: str, value: Any):
        """Store value in key-value store."""
        json_value = json.dumps(value)
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO kv_store (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (key, json_value),
            )
            conn.commit()

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve value from key-value store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM kv_store WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default

    def delete(self, key: str):
        """Delete value from key-value store."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM kv_store WHERE key = ?", (key,))
            conn.commit()

    def save_conversation(self, session_id: str, memory: ConversationMemory):
        """Save conversation memory to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM conversations WHERE session_id = ?", (session_id,)
            )

            for msg in memory.messages:
                cursor.execute(
                    """
                    INSERT INTO conversations (session_id, role, content, metadata, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (
                        session_id,
                        msg.role,
                        msg.content,
                        json.dumps(msg.metadata),
                        msg.timestamp,
                    ),
                )

            if memory.summary:
                self.set(f"conv_summary_{session_id}", memory.summary)

            conn.commit()

    def load_conversation(self, session_id: str) -> Optional[ConversationMemory]:
        """Load conversation memory from database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content, metadata, timestamp
                FROM conversations
                WHERE session_id = ?
                ORDER BY timestamp
            """,
                (session_id,),
            )

            rows = cursor.fetchall()
            if not rows:
                return None

            memory = ConversationMemory()
            for role, content, metadata_json, timestamp in rows:
                msg = ChatMessage(
                    role=role,
                    content=content,
                    timestamp=timestamp,
                    metadata=json.loads(metadata_json) if metadata_json else {},
                )
                memory.messages.append(msg)

            memory.summary = self.get(f"conv_summary_{session_id}", "")
            return memory

    def save_task(self, task_id: str, name: str, status: str, data: Dict[str, Any]):
        """Save or update task."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            completed_at = datetime.now().isoformat() if status == "completed" else None
            cursor.execute(
                """
                INSERT OR REPLACE INTO tasks (task_id, name, status, data, completed_at)
                VALUES (?, ?, ?, ?, ?)
            """,
                (task_id, name, status, json.dumps(data), completed_at),
            )
            conn.commit()

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT task_id, name, status, data, created_at, completed_at
                FROM tasks WHERE task_id = ?
            """,
                (task_id,),
            )

            row = cursor.fetchone()
            if row:
                return {
                    "task_id": row[0],
                    "name": row[1],
                    "status": row[2],
                    "data": json.loads(row[3]) if row[3] else {},
                    "created_at": row[4],
                    "completed_at": row[5],
                }
            return None

    def get_recent_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent tasks."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT task_id, name, status, data, created_at, completed_at
                FROM tasks ORDER BY created_at DESC LIMIT ?
            """,
                (limit,),
            )

            return [
                {
                    "task_id": row[0],
                    "name": row[1],
                    "status": row[2],
                    "data": json.loads(row[3]) if row[3] else {},
                    "created_at": row[4],
                    "completed_at": row[5],
                }
                for row in cursor.fetchall()
            ]

    def set_setting(self, key: str, value: Any):
        """Save setting."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (key, json.dumps(value)),
            )
            conn.commit()

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get setting."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return default


_persistent_store: Optional[PersistentStore] = None


def get_persistent_store(db_path: Optional[str] = None) -> PersistentStore:
    """Get global persistent store singleton."""
    global _persistent_store
    requested_path = Path(db_path or aura_path("aura_data.db")).expanduser().resolve()
    if _persistent_store is None or _persistent_store.db_path.resolve() != requested_path:
        _persistent_store = PersistentStore(str(requested_path))
    return _persistent_store


def reset_persistent_store():
    """Reset the persistent store singleton (for testing)."""
    global _persistent_store
    _persistent_store = None


__all__ = [
    "ChatMessage",
    "ChromaDBVectorStore",
    "ConstitutionValidator",
    "ConversationMemory",
    "FAISSVectorStore",
    "InMemoryState",
    "KeywordVectorStore",
    "LearnedRule",
    "MemoryService",
    "NotebookManager",
    "NotebookService",
    "PersistentStore",
    "SearchResult",
    "VectorStore",
    "create_vector_store",
    "detect_best_backend",
    "get_memory_service",
    "get_persistent_store",
    "reset_memory_service",
    "reset_persistent_store",
]
