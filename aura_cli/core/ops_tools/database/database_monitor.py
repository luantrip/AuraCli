"""Database monitor for Aura CLI.

Provides performance, connection and health monitoring for databases.
"""

from dataclasses import dataclass
from datetime import datetime
import os
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

if TYPE_CHECKING:
    from aura_cli.core.ops_tools.database.query_executor import (
        DatabaseConnection,
        QueryExecutor,
    )

logger = get_logger(__name__)


@dataclass
class DatabaseMetrics:
    """Database metrics (db_name, connections, active_queries, etc.)."""

    db_name: str
    connections: int = 0
    active_queries: int = 0
    cache_hit_ratio: float = 0.0
    size: int = 0
    uptime: float = 0.0
    table_count: int = 0
    index_count: int = 0


class DatabaseMonitor:
    """Monitors database health and performance."""

    METRICS_QUERIES: ClassVar[dict] = {
        "sqlite": {
            "tables": "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table'",
            "indexes": "SELECT COUNT(*) as count FROM sqlite_master WHERE type='index'",
        },
        "postgresql": {
            "connections": """
                SELECT COUNT(*) as count
                FROM pg_stat_activity
                WHERE datname = current_database()
            """,
            "active_queries": """
                SELECT COUNT(*) as count
                FROM pg_stat_activity
                WHERE state = 'active' AND datname = current_database()
            """,
            "cache_hit": """
                SELECT
                    CASE WHEN blks_hit + blks_read = 0 THEN 0
                    ELSE blks_hit::float / (blks_hit + blks_read)
                    END as ratio
                FROM pg_stat_database
                WHERE datname = current_database()
            """,
            "size": """
                SELECT pg_database_size(current_database()) as size
            """,
            "tables": """
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """,
            "indexes": """
                SELECT COUNT(*) as count
                FROM pg_indexes
                WHERE schemaname = 'public'
            """,
        },
        "mysql": {
            "connections": """
                SELECT COUNT(*) as count
                FROM information_schema.processlist
            """,
            "active_queries": """
                SELECT COUNT(*) as count
                FROM information_schema.processlist
                WHERE command != 'Sleep'
            """,
            "size": """
                SELECT SUM(data_length + index_length) as size
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
            """,
            "tables": """
                SELECT COUNT(*) as count
                FROM information_schema.tables
                WHERE table_schema = DATABASE()
            """,
            "indexes": """
                SELECT COUNT(DISTINCT index_name) as count
                FROM information_schema.statistics
                WHERE table_schema = DATABASE()
            """,
        },
    }

    def __init__(self) -> None:
        """Initialise the database monitor."""
        self.stats = get_stats()
        self.metrics_history: List[DatabaseMetrics] = []
        logger.info("DatabaseMonitor initialized")

    def _get_executor(self) -> "QueryExecutor":
        """Return or create the SQL executor."""
        from aura_cli.core.ops_tools.database.query_executor import QueryExecutor

        return QueryExecutor()

    def collect_metrics(
        self, connection: "DatabaseConnection"
    ) -> Optional[DatabaseMetrics]:
        """Collect real metrics from the database."""
        from aura_cli.core.ui import display_tool_call

        display_tool_call("collect_metrics", {"database": connection.database})

        db_type = connection.db_type.lower()
        executor = self._get_executor()

        metrics = DatabaseMetrics(db_name=connection.database)

        try:
            queries = self.METRICS_QUERIES.get(db_type, {})

            if db_type == "sqlite" and os.path.exists(connection.database):
                metrics.size = os.path.getsize(connection.database)

            for metric_name, query in queries.items():
                try:
                    result = executor.execute_query(query, connection)
                    if result.success and result.rows:
                        row = result.rows[0]
                        value = next(iter(row.values())) if row else 0

                        if metric_name == "connections":
                            metrics.connections = int(value or 0)
                        elif metric_name == "active_queries":
                            metrics.active_queries = int(value or 0)
                        elif metric_name == "cache_hit":
                            metrics.cache_hit_ratio = float(value or 0)
                        elif metric_name == "size":
                            metrics.size = int(value or 0)
                        elif metric_name == "tables":
                            metrics.table_count = int(value or 0)
                        elif metric_name == "indexes":
                            metrics.index_count = int(value or 0)
                except Exception as e:
                    logger.debug(f"Error collecting metric {metric_name}: {e}")

            self.metrics_history.append(metrics)
            if len(self.metrics_history) > 100:
                self.metrics_history = self.metrics_history[-100:]

            logger.debug(f"Métricas coletadas para {connection.database}")
            self.stats.track_tool_usage("database_monitor")

            return metrics

        except Exception as e:
            logger.error(f"Error collecting metrics: {e}", exc_info=True)
            return None

    def check_health(self, connection: "DatabaseConnection") -> Dict[str, Any]:
        """Check database health and return a status report."""
        from aura_cli.core.ui import display_tool_call

        display_tool_call("check_health", {"database": connection.database})

        executor = self._get_executor()

        health_result: Dict[str, Any] = {
            "status": "unknown",
            "database": connection.database,
            "db_type": connection.db_type,
            "timestamp": datetime.now().isoformat(),
            "checks": {},
        }

        try:
            test_result = executor.test_connection(connection)
            health_result["checks"]["connection"] = test_result.success

            if not test_result.success:
                health_result["status"] = "unhealthy"
                health_result["error"] = test_result.error
                return health_result
        except Exception as e:
            health_result["status"] = "unhealthy"
            health_result["error"] = str(e)
            return health_result

        metrics = self.collect_metrics(connection)
        if metrics:
            health_result["checks"]["metrics"] = True
            health_result["metrics"] = {
                "connections": metrics.connections,
                "active_queries": metrics.active_queries,
                "size_mb": round(metrics.size / 1024 / 1024, 2),
                "table_count": metrics.table_count,
            }

            issues = []

            if connection.db_type.lower() in ("postgresql", "mysql"):
                if metrics.connections > 100:
                    issues.append("Alto número de conexões")
                if metrics.active_queries > 50:
                    issues.append("Muitas queries ativas")
                if metrics.cache_hit_ratio < 0.8:
                    issues.append("Cache hit ratio baixo")

            if issues:
                health_result["status"] = "degraded"
                health_result["issues"] = issues
            else:
                health_result["status"] = "healthy"
        else:
            health_result["checks"]["metrics"] = False
            health_result["status"] = "degraded"
            health_result["issues"] = ["Não foi possível coletar métricas"]

        return health_result

    def get_performance_summary(self) -> Dict[str, Any]:
        """Return a performance summary as a dict."""
        if not self.metrics_history:
            return {"message": "Nenhuma métrica coletada ainda"}

        latest = self.metrics_history[-1]

        summary = {
            "database": latest.db_name,
            "current": {
                "connections": latest.connections,
                "active_queries": latest.active_queries,
                "cache_hit_ratio": round(latest.cache_hit_ratio, 4),
                "size_mb": round(latest.size / 1024 / 1024, 2)
                if latest.size > 0
                else 0,
                "table_count": latest.table_count,
                "index_count": latest.index_count,
            },
            "history_count": len(self.metrics_history),
        }

        if len(self.metrics_history) >= 5:
            recent = self.metrics_history[-5:]
            avg_connections = sum(m.connections for m in recent) / len(recent)
            avg_queries = sum(m.active_queries for m in recent) / len(recent)

            summary["trends"] = {
                "avg_connections": round(avg_connections, 1),
                "avg_active_queries": round(avg_queries, 1),
                "connection_trend": "stable"
                if abs(latest.connections - avg_connections) < 5
                else (
                    "increasing"
                    if latest.connections > avg_connections
                    else "decreasing"
                ),
            }

        return summary

    def get_slow_queries(
        self, connection: "DatabaseConnection", threshold_ms: int = 1000
    ) -> List[Dict[str, Any]]:
        """Return slow queries (PostgreSQL/MySQL only)."""
        executor = self._get_executor()
        db_type = connection.db_type.lower()

        # threshold_ms is interpolated into the SQL (interval/time literals cannot be
        # bind parameters here); coerce to int so only a numeric value can reach the
        # query, eliminating any injection vector.
        try:
            threshold_ms = int(threshold_ms)
        except (TypeError, ValueError) as err:
            raise ValueError(f"invalid threshold_ms: {threshold_ms!r}") from err

        if db_type == "postgresql":
            # threshold_ms is coerced to int above; no untrusted input reaches the query.
            query = f"""
                SELECT
                    pid,
                    now() - query_start as duration,
                    state,
                    LEFT(query, 100) as query_preview
                FROM pg_stat_activity
                WHERE state = 'active'
                AND query_start < now() - interval '{threshold_ms} milliseconds'
                ORDER BY query_start
                LIMIT 10
            """  # nosec B608
        elif db_type == "mysql":
            # threshold_ms is coerced to int above; no untrusted input reaches the query.
            query = f"""
                SELECT
                    id as pid,
                    time as duration_seconds,
                    state,
                    LEFT(info, 100) as query_preview
                FROM information_schema.processlist
                WHERE command != 'Sleep'
                AND time > {threshold_ms / 1000}
                ORDER BY time DESC
                LIMIT 10
            """  # nosec B608
        else:
            return []

        try:
            result = executor.execute_query(query, connection)
            if result.success:
                return result.rows
        except Exception as e:
            logger.debug(f"Error fetching slow queries: {e}")

        return []


_monitor_instance: Optional[DatabaseMonitor] = None


def get_database_monitor() -> DatabaseMonitor:
    """
    Get or create DatabaseMonitor instance (singleton).

    Returns:
        DatabaseMonitor instance
    """
    global _monitor_instance
    if _monitor_instance is None:
        _monitor_instance = DatabaseMonitor()
    return _monitor_instance
