"""Log aggregator for Aura CLI.

Provides collection, aggregation and analysis of logs from multiple sources.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class LogLevel(Enum):
    """Log level enum."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


@dataclass
class LogEntry:
    """Log entry (timestamp, level, source, message)."""

    timestamp: datetime
    level: LogLevel
    source: str
    message: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class LogsAggregator:
    """Log aggregator from multiple sources with filtering and search."""

    def __init__(self):
        """Initialise the log aggregator."""
        self.logs: List[LogEntry] = []
        self.stats = get_stats()

        logger.info("LogsAggregator initialized")

    def add_log(
        self,
        level: LogLevel,
        source: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add a log entry."""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            source=source,
            message=message,
            metadata=metadata or {},
        )

        self.logs.append(entry)

        if len(self.logs) > 10000:
            self.logs = self.logs[-10000:]

        logger.debug(f"Log adicionado: {level.value} de {source}")

    def search_logs(
        self,
        query: str,
        level: Optional[LogLevel] = None,
        source: Optional[str] = None,
        limit: int = 100,
    ) -> List[LogEntry]:
        """Search logs by text query, level and source."""
        results = self.logs.copy()

        if level:
            results = [r for r in results if r.level == level]

        if source:
            results = [r for r in results if r.source == source]

        try:
            pattern = re.compile(query, re.IGNORECASE)
            results = [r for r in results if pattern.search(r.message)]
        except re.error:
            query_lower = query.lower()
            results = [r for r in results if query_lower in r.message.lower()]

        results.sort(key=lambda r: r.timestamp, reverse=True)

        return results[:limit]

    def aggregate_by_level(self) -> Dict[str, int]:
        """Return log counts grouped by level."""
        counts: dict[str, int] = {}
        for entry in self.logs:
            level = entry.level.value
            counts[level] = counts.get(level, 0) + 1

        return counts

    def aggregate_by_source(self) -> Dict[str, int]:
        """
        Agrega logs por fonte.

        Returns:
            Contagem por fonte
        """
        counts: dict[str, int] = {}
        for entry in self.logs:
            source = entry.source
            counts[source] = counts.get(source, 0) + 1

        return counts

    def get_recent_errors(self, limit: int = 50) -> List[LogEntry]:
        """Return recent error log entries."""
        errors = [
            e for e in self.logs if e.level in [LogLevel.ERROR, LogLevel.CRITICAL]
        ]

        errors.sort(key=lambda e: e.timestamp, reverse=True)

        return errors[:limit]

    def get_statistics(self) -> Dict[str, Any]:
        """Return log aggregation statistics as a dict."""
        return {
            "total_logs": len(self.logs),
            "by_level": self.aggregate_by_level(),
            "by_source": self.aggregate_by_source(),
            "recent_errors": len(self.get_recent_errors()),
        }


# Factory function for singleton pattern
_aggregator_instance: Optional[LogsAggregator] = None


def get_logs_aggregator() -> LogsAggregator:
    """
    Get or create LogsAggregator instance (singleton).

    Returns:
        LogsAggregator instance
    """
    global _aggregator_instance
    if _aggregator_instance is None:
        _aggregator_instance = LogsAggregator()
    return _aggregator_instance
