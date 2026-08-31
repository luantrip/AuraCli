"""Universal SQL query executor for the Ops agent.

Uses SQLAlchemy Core (not ORM) to support SQLite (default/built-in),
PostgreSQL (psycopg2), MySQL (pymysql) and other SQLAlchemy-compatible
databases through a unified connection-string interface.
"""

from contextlib import contextmanager
from dataclasses import dataclass, field
import os
import re
from typing import Any, Dict, Generator, List, Optional

from rich.console import Console
from rich.table import Table

from aura_cli.core.logger import get_logger
from aura_cli.core.paths import aura_path
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()

# SQL identifiers (table names) cannot be passed as bind parameters, so any value
# interpolated into a statement must be validated against a strict allowlist to
# prevent SQL injection. Allows an optional single schema qualifier.
_SQL_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?$")


def _validate_identifier(name: str) -> str:
    """Validate a SQL identifier (e.g. table name) before interpolation.

    Raises:
        ValueError: if ``name`` is not a safe SQL identifier.
    """
    if not isinstance(name, str) or not _SQL_IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid table name/SQL identifier: {name!r}")
    return name


DEFAULT_DB_PATH = str(aura_path("aura_data.db"))


@dataclass
class DatabaseConnection:
    """
    Database connection configuration.

    Supports both individual parameters and connection strings.
    For SQLite, only 'database' (file path) is needed.

    Attributes:
        db_type: Database type (sqlite, postgresql, mysql, oracle, mssql)
        host: Database host (not used for SQLite)
        port: Database port (defaults vary by db_type)
        database: Database name or file path (SQLite)
        username: Database user
        password: Database password
        connection_string: Full SQLAlchemy connection URL (overrides other fields)
        pool_size: Connection pool size (for production databases)
        echo: If True, log all SQL statements
    """

    db_type: str = "sqlite"
    host: str = "localhost"
    port: Optional[int] = None
    database: str = DEFAULT_DB_PATH
    username: str = ""
    password: Optional[str] = None
    connection_string: Optional[str] = None
    pool_size: int = 5
    echo: bool = False

    def get_connection_url(self) -> str:
        """
        Build SQLAlchemy connection URL.

        Returns:
            SQLAlchemy-compatible connection string
        """
        if self.connection_string:
            return self.connection_string

        db_type = self.db_type.lower()

        if db_type == "sqlite":
            db_path = os.path.expanduser(self.database)
            os.makedirs(os.path.dirname(db_path) or ".", exist_ok=True)
            return f"sqlite:///{db_path}"

        elif db_type == "postgresql":
            port = self.port or 5432
            auth = f"{self.username}:{self.password}@" if self.username else ""
            return f"postgresql://{auth}{self.host}:{port}/{self.database}"

        elif db_type == "mysql":
            port = self.port or 3306
            auth = f"{self.username}:{self.password}@" if self.username else ""
            return f"mysql+mysqlconnector://{auth}{self.host}:{port}/{self.database}"

        elif db_type == "oracle":
            port = self.port or 1521
            auth = f"{self.username}:{self.password}@" if self.username else ""
            return f"oracle+cx_oracle://{auth}{self.host}:{port}/{self.database}"

        elif db_type == "mssql":
            port = self.port or 1433
            auth = f"{self.username}:{self.password}@" if self.username else ""
            return f"mssql+pyodbc://{auth}{self.host}:{port}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server"

        else:
            raise ValueError(
                f"Database type '{db_type}' not supported. "
                f"Use: sqlite, postgresql, mysql, oracle, mssql"
            )


@dataclass
class QueryResult:
    """
    Result of a query execution.

    Attributes:
        success: Whether execution succeeded
        rows: Result rows as list of dictionaries
        columns: Column names
        row_count: Rows affected/returned
        duration: Execution time in seconds
        error: Error message if failed
    """

    success: bool
    rows: List[Dict[str, Any]] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    row_count: int = 0
    duration: float = 0.0
    error: Optional[str] = None

    def to_table(self, title: str = "Query Results") -> Table:
        """Convert results to Rich Table for display."""
        table = Table(title=title)

        for col in self.columns:
            table.add_column(col)

        for row in self.rows[:100]:  # Limit display
            table.add_row(*[str(row.get(col, "")) for col in self.columns])

        if len(self.rows) > 100:
            table.add_row(*["..." for _ in self.columns])

        return table


_sqlalchemy_available = None
_engines: Dict[str, Any] = {}


def _check_sqlalchemy() -> bool:
    """Check if SQLAlchemy is available (now always True - essential dependency)."""
    global _sqlalchemy_available
    if _sqlalchemy_available is None:
        _sqlalchemy_available = True
    return _sqlalchemy_available


def _get_engine(connection: DatabaseConnection):
    """Get or create SQLAlchemy engine with connection pooling."""
    from sqlalchemy import create_engine
    from sqlalchemy.pool import QueuePool, StaticPool

    url = connection.get_connection_url()

    cache_key = url
    if cache_key in _engines:
        return _engines[cache_key]

    if connection.db_type.lower() == "sqlite":
        # SQLite needs special handling for thread safety
        engine = create_engine(
            url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=connection.echo,
        )
    else:
        # Production databases use connection pooling
        engine = create_engine(
            url,
            pool_size=connection.pool_size,
            poolclass=QueuePool,
            echo=connection.echo,
        )

    _engines[cache_key] = engine
    return engine


class QueryExecutor:
    """
    Universal SQL Query Executor using SQLAlchemy.

    Features:
        - Database-agnostic execution via SQLAlchemy Core
        - Connection pooling for production databases
        - Parameterized queries (SQL injection protection)
        - Transaction support
        - Query validation

    Default: SQLite at ~/.aura/aura_data.db
    """

    def __init__(self, default_connection: Optional[DatabaseConnection] = None) -> None:
        """
        Initialize executor.

        Args:
            default_connection: Default connection to use if none provided
        """
        self.stats = get_stats()
        self.default_connection = default_connection or DatabaseConnection()
        logger.info(
            f"QueryExecutor initialized (default: {self.default_connection.db_type})"
        )

    def execute_query(
        self,
        query: str,
        connection: Optional[DatabaseConnection] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """
        Execute a SQL query.

        Args:
            query: SQL query (use :param_name for parameters)
            connection: Database connection (uses default if None)
            parameters: Query parameters as dict

        Returns:
            QueryResult with execution results

        Example:
            result = executor.execute_query(
                "SELECT * FROM users WHERE name = :name AND age > :age",
                parameters={"name": "John", "age": 18}
            )
        """
        import time

        from aura_cli.core.ui import display_tool_call

        connection = connection or self.default_connection
        start_time = time.time()

        display_tool_call(
            "execute_query",
            {
                "db_type": connection.db_type,
                "database": connection.database,
                "query_preview": query[:100] + ("..." if len(query) > 100 else ""),
            },
        )

        validation = self._validate_query(query)
        if not validation["valid"]:
            return QueryResult(
                success=False,
                duration=time.time() - start_time,
                error=validation["error"],
            )

        try:
            from sqlalchemy import text

            engine = _get_engine(connection)

            with engine.connect() as conn:
                if parameters:
                    result = conn.execute(text(query), parameters)
                else:
                    result = conn.execute(text(query))

                query_upper = query.strip().upper()
                is_select = query_upper.startswith(("SELECT", "WITH", "PRAGMA"))

                if is_select and result.returns_rows:
                    columns = list(result.keys())
                    rows = [dict(row._mapping) for row in result.fetchall()]
                    row_count = len(rows)
                else:
                    columns = []
                    rows = []
                    row_count = result.rowcount if result.rowcount >= 0 else 0
                    conn.commit()

                duration = time.time() - start_time

                logger.info(f"Query executed: {row_count} rows ({duration:.3f}s)")
                console.print(f"[green]✅ Query executed: {row_count} rows[/green]")

                self.stats.track_tool_usage("query_executor")

                return QueryResult(
                    success=True,
                    rows=rows,
                    columns=columns,
                    row_count=row_count,
                    duration=duration,
                )

        except Exception as e:
            error_msg = f"Query execution error: {e}"
            logger.error(error_msg, exc_info=True)
            return QueryResult(
                success=False,
                duration=time.time() - start_time,
                error=error_msg,
            )

    def _execute_raw(
        self,
        query: str,
        connection: DatabaseConnection,
        parameters: Optional[Dict[str, Any]],
    ) -> QueryResult:
        """Fallback execution using raw database drivers."""
        import time

        start_time = time.time()
        db_type = connection.db_type.lower()

        try:
            if db_type == "sqlite":
                import sqlite3

                conn = sqlite3.connect(connection.database)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                if parameters:
                    cursor.execute(query, parameters)
                else:
                    cursor.execute(query)

                query_upper = query.strip().upper()
                is_select = query_upper.startswith("SELECT")

                if is_select:
                    rows_raw = cursor.fetchall()
                    columns = (
                        [desc[0] for desc in cursor.description]
                        if cursor.description
                        else []
                    )
                    rows = [dict(row) for row in rows_raw]
                    row_count = len(rows)
                else:
                    conn.commit()
                    columns = []
                    rows = []
                    row_count = cursor.rowcount

                cursor.close()
                conn.close()

                return QueryResult(
                    success=True,
                    rows=rows,
                    columns=columns,
                    row_count=row_count,
                    duration=time.time() - start_time,
                )

            else:
                return QueryResult(
                    success=False,
                    error=f"Raw driver fallback not implemented for {db_type}. Install SQLAlchemy.",
                    duration=time.time() - start_time,
                )

        except Exception as e:
            return QueryResult(
                success=False,
                error=f"Raw execution error: {e}",
                duration=time.time() - start_time,
            )

    def execute_many(
        self,
        query: str,
        parameters_list: List[Dict[str, Any]],
        connection: Optional[DatabaseConnection] = None,
    ) -> QueryResult:
        """
        Execute a query multiple times with different parameters.

        Args:
            query: SQL query with :param_name placeholders
            parameters_list: List of parameter dictionaries
            connection: Database connection

        Returns:
            QueryResult with total affected count
        """
        import time

        connection = connection or self.default_connection
        start_time = time.time()

        try:
            from sqlalchemy import text

            engine = _get_engine(connection)
            total_affected = 0

            with engine.connect() as conn:
                for params in parameters_list:
                    result = conn.execute(text(query), params)
                    if result.rowcount >= 0:
                        total_affected += result.rowcount

                conn.commit()

            return QueryResult(
                success=True,
                row_count=total_affected,
                duration=time.time() - start_time,
            )

        except Exception as e:
            return QueryResult(
                success=False,
                error=f"Batch execution error: {e}",
                duration=time.time() - start_time,
            )

    @contextmanager
    def transaction(
        self, connection: Optional[DatabaseConnection] = None
    ) -> Generator[Any, None, None]:
        """
        Context manager for transactions.

        Args:
            connection: Database connection

        Yields:
            SQLAlchemy connection object

        Example:
            with executor.transaction() as conn:
                conn.execute(text("INSERT INTO users ..."))
                conn.execute(text("INSERT INTO logs ..."))
        """
        connection = connection or self.default_connection
        engine = _get_engine(connection)

        with engine.begin() as conn:
            yield conn

    def _validate_query(self, query: str) -> Dict[str, Any]:
        """Validate query for dangerous operations."""
        if not query or not query.strip():
            return {"valid": False, "error": "Empty query"}

        dangerous_keywords = [
            "DROP DATABASE",
            "DROP SCHEMA",
        ]

        query_upper = query.upper()

        for keyword in dangerous_keywords:
            if keyword in query_upper:
                return {
                    "valid": False,
                    "error": f"Blocked dangerous command: {keyword}. "
                    f"Use execute_dangerous_query() if necessary.",
                }

        return {"valid": True}

    def execute_dangerous_query(
        self,
        query: str,
        connection: Optional[DatabaseConnection] = None,
        confirm: bool = False,
    ) -> QueryResult:
        """
        Execute potentially dangerous queries after confirmation.

        Args:
            query: SQL query (may contain DROP, TRUNCATE, etc.)
            connection: Database connection
            confirm: Must be True to proceed

        Returns:
            QueryResult
        """
        if not confirm:
            return QueryResult(
                success=False,
                error="Dangerous query requires confirm=True",
            )

        sql_injection_patterns = [
            r"';?\s*(--|#|/\*|\*/)",  # SQL comment injection
            r"union\s+select",  # UNION SELECT injection
            r"exec\s*\(",  # EXEC injection
            r"xp_\w+",  # Extended stored procedures
            r"sp_\w+",  # Stored procedures (some may be dangerous)
            r"0x[0-9a-f]+",  # Hex-encoded strings (common in SQL injection)
        ]

        import re

        query_upper = query.upper()
        for pattern in sql_injection_patterns:
            if re.search(pattern, query_upper, re.IGNORECASE):
                logger.warning(
                    f"SQL injection pattern detected in dangerous query: {pattern}"
                )
                return QueryResult(
                    success=False,
                    error="Query blocked: potential SQL injection pattern detected",
                )

        statements = [s.strip() for s in query.split(";") if s.strip()]
        if len(statements) > 1:
            logger.warning("Multiple SQL statements detected in dangerous query")
            return QueryResult(
                success=False,
                error="Query blocked: multiple statements not allowed in dangerous queries",
            )

        import time

        from sqlalchemy import text

        connection = connection or self.default_connection
        start_time = time.time()

        try:
            engine = _get_engine(connection)

            with engine.begin() as conn:
                result = conn.execute(text(query))
                row_count = result.rowcount if result.rowcount >= 0 else 0

            logger.warning(f"Dangerous query executed: {query[:100]}")

            return QueryResult(
                success=True,
                row_count=row_count,
                duration=time.time() - start_time,
            )

        except Exception as e:
            logger.error(f"Dangerous query execution error: {e}")
            return QueryResult(
                success=False,
                error=f"Dangerous query error: {e}",
                duration=time.time() - start_time,
            )

    def test_connection(
        self, connection: Optional[DatabaseConnection] = None
    ) -> QueryResult:
        """
        Test database connection.

        Args:
            connection: Database connection to test

        Returns:
            QueryResult indicating success/failure
        """
        connection = connection or self.default_connection
        return self.execute_query("SELECT 1 AS test", connection)

    def get_tables(
        self, connection: Optional[DatabaseConnection] = None
    ) -> QueryResult:
        """
        List tables in database.

        Args:
            connection: Database connection

        Returns:
            QueryResult with table names
        """
        connection = connection or self.default_connection
        db_type = connection.db_type.lower()

        if db_type == "sqlite":
            query = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        elif db_type == "postgresql":
            query = "SELECT tablename AS name FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"
        elif db_type == "mysql":
            query = "SHOW TABLES"
        else:
            query = "SELECT table_name AS name FROM information_schema.tables WHERE table_schema = 'public'"

        return self.execute_query(query, connection)

    def describe_table(
        self,
        table_name: str,
        connection: Optional[DatabaseConnection] = None,
    ) -> QueryResult:
        """
        Get table schema information.

        Args:
            table_name: Name of table to describe
            connection: Database connection

        Returns:
            QueryResult with column information
        """
        connection = connection or self.default_connection
        db_type = connection.db_type.lower()

        # table_name is a SQL identifier and cannot be a bind parameter; validate it
        # against a strict allowlist before any interpolation to prevent injection.
        safe_table = _validate_identifier(table_name)

        if db_type == "sqlite":
            query = f"PRAGMA table_info({safe_table})"
            return self.execute_query(query, connection)
        elif db_type == "postgresql":
            # Value comparison can be safely parameterized.
            query = """
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = :table_name
                ORDER BY ordinal_position
            """
            return self.execute_query(
                query, connection, parameters={"table_name": safe_table}
            )
        elif db_type == "mysql":
            query = f"DESCRIBE {safe_table}"
        else:
            query = f"DESCRIBE {safe_table}"

        return self.execute_query(query, connection)


_default_executor: Optional[QueryExecutor] = None


def get_executor() -> QueryExecutor:
    """Get default QueryExecutor instance."""
    global _default_executor
    if _default_executor is None:
        _default_executor = QueryExecutor()
    return _default_executor


get_query_executor = get_executor
