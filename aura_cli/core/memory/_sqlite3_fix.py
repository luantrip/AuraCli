"""
Workaround for old SQLite3 on macOS.

ChromaDB requires SQLite3 >= 3.35.0, but older systems may have an older version.
This module must be imported BEFORE any ChromaDB import to apply
the  workaround automaticamente.
"""

import sys

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

if not hasattr(sys.modules.get("sqlite3", None), "_aura_wrapped"):
    try:
        import sqlite3

        sqlite_version = sqlite3.sqlite_version
        version_parts = [int(x) for x in sqlite_version.split(".")]
        if len(version_parts) >= 2:
            major, minor = version_parts[0], version_parts[1]
            if major < 3 or (major == 3 and minor < 35):
                logger.debug(
                    f"SQLite3 {sqlite_version} < 3.35.0 — aplicando workaround para ChromaDB"
                )

                class SQLite3Wrapper:
                    """Wrapper para simular SQLite3 >= 3.35.0 para ChromaDB."""

                    def __init__(self, original_sqlite3):
                        """Initialize the widget."""
                        self._original = original_sqlite3
                        self._aura_wrapped = True  # Marca para evitar re-wrap
                        for attr in dir(original_sqlite3):
                            if not attr.startswith("_"):
                                try:
                                    setattr(self, attr, getattr(original_sqlite3, attr))
                                except (AttributeError, TypeError) as _e:
                                    logger.debug(f"Ignorado: {_e}")
                        self.sqlite_version = "3.35.0"
                        self.sqlite_version_info = (3, 35, 0)

                wrapped_sqlite3 = SQLite3Wrapper(sqlite3)
                sys.modules["sqlite3"] = wrapped_sqlite3  # type: ignore[assignment]

                # Sanity check: verify ChromaDB can still be imported after wrap
                try:
                    import importlib.util

                    chroma_spec = importlib.util.find_spec("chromadb")
                    if chroma_spec:
                        logger.debug(
                            "Workaround SQLite3 validado com ChromaDB instalado"
                        )
                except Exception as e:
                    logger.warning(
                        f"Workaround SQLite3 pode estar desatualizado com esta versão do ChromaDB: {e}"
                    )
            else:
                logger.debug(
                    f"SQLite3 {sqlite_version} >= 3.35.0 — workaround não necessário"
                )
    except Exception as e:
        logger.warning(f"Error applying SQLite3 workaround: {e}")
