"""Cross-session telemetry persistence to a local SQLite database.

Records every session, turn, and tool call to ``~/.aura/telemetry.db``
automatically. Zero cloud, zero network. No message bodies are stored.

Inspired by the ``opencode-telemetry`` plugin for OpenCode, adapted to
AuraCli's observability layer.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
import sqlite3
import threading
from typing import Any, Optional

from aura_cli.application.artifacts import get_aura_home

logger = logging.getLogger(__name__)

_DEFAULT_DB_PATH: Path | None = None  # lazily computed via get_aura_home()


def _default_db_path() -> Path:
    return get_aura_home() / "telemetry.db"
_DEFAULT_RETENTION_DAYS = 90
_SCHEMA_VERSION = 1

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    provider TEXT,
    model TEXT,
    total_tokens INTEGER DEFAULT 0,
    total_cost REAL DEFAULT 0.0,
    tool_calls INTEGER DEFAULT 0,
    agent_type TEXT,
    parent_session_id TEXT
);

CREATE TABLE IF NOT EXISTS turns (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    input_tokens INTEGER DEFAULT 0,
    output_tokens INTEGER DEFAULT 0,
    cost REAL DEFAULT 0.0,
    tool_name TEXT,
    duration_ms INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at);
"""


@dataclass(frozen=True)
class SessionRecord:
    id: str
    started_at: str
    provider: Optional[str] = None
    model: Optional[str] = None
    agent_type: Optional[str] = None
    parent_session_id: Optional[str] = None


@dataclass(frozen=True)
class TurnRecord:
    id: str
    session_id: str
    turn_number: int
    started_at: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0
    tool_name: Optional[str] = None
    duration_ms: int = 0


class SessionTelemetry:
    """Thread-safe SQLite telemetry store for cross-session observability.

    The database is created lazily on first write. All operations are
    guarded by a lock to support concurrent workers.
    """

    def __init__(
        self,
        db_path: str | Path | None = None,
        *,
        retention_days: int = _DEFAULT_RETENTION_DAYS,
        enabled: bool = True,
    ) -> None:
        self.db_path = Path(db_path) if db_path else _default_db_path()
        self.retention_days = retention_days
        self.enabled = enabled
        self._lock = threading.Lock()
        self._initialized = False

    def _ensure_schema(self) -> None:
        """Create the database and tables if they do not exist."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.executescript(_SCHEMA_SQL)
                conn.execute(
                    "INSERT OR IGNORE INTO schema_meta(key, value) VALUES (?, ?)",
                    ("schema_version", str(_SCHEMA_VERSION)),
                )
                conn.commit()
            finally:
                conn.close()
            self._initialized = True
            logger.debug("Telemetry DB initialized at %s", self.db_path)

    def record_session(
        self,
        session_id: str,
        *,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        agent_type: Optional[str] = None,
        parent_session_id: Optional[str] = None,
    ) -> None:
        """Insert a new session record."""
        if not self.enabled:
            return
        self._ensure_schema()
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO sessions "
                    "(id, started_at, provider, model, agent_type, parent_session_id) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        session_id,
                        datetime.now().isoformat(),
                        provider,
                        model,
                        agent_type,
                        parent_session_id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def finalize_session(
        self,
        session_id: str,
        *,
        total_tokens: int = 0,
        total_cost: float = 0.0,
        tool_calls: int = 0,
    ) -> None:
        """Update a session record with final totals."""
        if not self.enabled:
            return
        self._ensure_schema()
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    "UPDATE sessions SET ended_at = ?, "
                    "total_tokens = ?, total_cost = ?, tool_calls = ? "
                    "WHERE id = ?",
                    (
                        datetime.now().isoformat(),
                        total_tokens,
                        total_cost,
                        tool_calls,
                        session_id,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def record_turn(
        self,
        turn_id: str,
        session_id: str,
        turn_number: int,
        *,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost: float = 0.0,
        tool_name: Optional[str] = None,
        duration_ms: int = 0,
    ) -> None:
        """Insert a turn record."""
        if not self.enabled:
            return
        self._ensure_schema()
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    "INSERT OR REPLACE INTO turns "
                    "(id, session_id, turn_number, started_at, "
                    "input_tokens, output_tokens, cost, tool_name, duration_ms) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        turn_id,
                        session_id,
                        turn_number,
                        datetime.now().isoformat(),
                        input_tokens,
                        output_tokens,
                        cost,
                        tool_name,
                        duration_ms,
                    ),
                )
                conn.commit()
            finally:
                conn.close()

    def get_session_cost(self, session_id: str) -> Optional[dict[str, Any]]:
        """Return cost breakdown for a single session."""
        if not self.enabled:
            return None
        self._ensure_schema()
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                row = conn.execute(
                    "SELECT * FROM sessions WHERE id = ?", (session_id,)
                ).fetchone()
                if row is None:
                    return None
                return dict(row)
            finally:
                conn.close()

    def get_cost_summary(self, days: int = 7) -> dict[str, Any]:
        """Return an aggregated cost summary for the last N days."""
        if not self.enabled:
            return {"enabled": False}
        self._ensure_schema()
        cutoff = datetime.now().isoformat()
        # Simple date math: subtract days from the ISO string prefix
        from datetime import timedelta

        cutoff_dt = datetime.now() - timedelta(days=days)
        cutoff = cutoff_dt.isoformat()
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT provider, model, "
                    "SUM(total_tokens) as tokens, "
                    "SUM(total_cost) as cost, "
                    "COUNT(*) as sessions "
                    "FROM sessions WHERE started_at >= ? "
                    "GROUP BY provider, model",
                    (cutoff,),
                ).fetchall()
                return {
                    "period_days": days,
                    "by_provider": [dict(row) for row in rows],
                    "total_cost": sum(row["cost"] or 0 for row in rows),
                    "total_tokens": sum(row["tokens"] or 0 for row in rows),
                    "total_sessions": sum(row["sessions"] for row in rows),
                }
            finally:
                conn.close()

    def get_chain_cost(self, parent_session_id: str) -> dict[str, Any]:
        """Return cost rollup for an orchestration chain."""
        if not self.enabled:
            return {"enabled": False}
        self._ensure_schema()
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row
            try:
                rows = conn.execute(
                    "SELECT id, total_tokens, total_cost, tool_calls, agent_type "
                    "FROM sessions WHERE parent_session_id = ?",
                    (parent_session_id,),
                ).fetchall()
                parent = conn.execute(
                    "SELECT total_tokens, total_cost, tool_calls "
                    "FROM sessions WHERE id = ?",
                    (parent_session_id,),
                ).fetchone()
                total_tokens = (parent["total_tokens"] or 0) if parent else 0
                total_cost = (parent["total_cost"] or 0) if parent else 0
                total_tools = (parent["tool_calls"] or 0) if parent else 0
                for row in rows:
                    total_tokens += row["total_tokens"] or 0
                    total_cost += row["total_cost"] or 0
                    total_tools += row["tool_calls"] or 0
                return {
                    "parent_session": parent_session_id,
                    "child_sessions": [dict(row) for row in rows],
                    "child_count": len(rows),
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "total_tool_calls": total_tools,
                }
            finally:
                conn.close()

    def prune_old_sessions(self) -> int:
        """Delete sessions older than retention_days. Returns count deleted."""
        if not self.enabled or self.retention_days == 0:
            return 0
        self._ensure_schema()
        from datetime import timedelta

        cutoff = (datetime.now() - timedelta(days=self.retention_days)).isoformat()
        with self._lock:
            conn = sqlite3.connect(str(self.db_path))
            try:
                conn.execute(
                    "DELETE FROM turns WHERE session_id IN "
                    "(SELECT id FROM sessions WHERE started_at < ?)",
                    (cutoff,),
                )
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE started_at < ?", (cutoff,)
                )
                conn.commit()
                return cursor.rowcount
            finally:
                conn.close()

    def close(self) -> None:
        """Mark the telemetry store as not initialized (for testing)."""
        self._initialized = False


__all__ = [
    "SessionRecord",
    "SessionTelemetry",
    "TurnRecord",
]
