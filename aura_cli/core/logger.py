"""Structured logging system for Aura CLI.

get_logger(__name__) returns a standard Logger with Rich console formatting
and daily file rotation under ~/.aura/logs/aura_YYYYMMDD.log.
Exceptions include full stack traces. Log level is configurable via
AURA_LOG_LEVEL env var.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import TYPE_CHECKING, Optional

from rich.console import Console
from rich.logging import RichHandler

from aura_cli.core.paths import aura_path

if TYPE_CHECKING:
    pass  # For future type imports

LOG_DIR = aura_path("logs")
LOG_FILE = LOG_DIR / f"aura_{datetime.now().strftime('%Y%m%d')}.log"


class _LazyDirectoryFileHandler(logging.FileHandler):
    """Open the log file only when the first record is actually emitted."""

    def __init__(self, filename: str) -> None:
        super().__init__(filename, encoding="utf-8", delay=True)

    def emit(self, record: logging.LogRecord) -> None:
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        super().emit(record)


class AuraFormatter(logging.Formatter):
    """Formatter customizado para logs da Aura CLI."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with structured information."""
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")

        log_line = (
            f"[{timestamp}] "
            f"[{record.levelname:8}] "
            f"[{record.name}] "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"

        return log_line


def setup_logger(
    name: str = "aura_cli",
    level: Optional[int] = None,
    log_to_file: bool = True,
    log_to_console: bool = True,
) -> logging.Logger:
    """Configure the structured logger for Aura CLI."""
    if level is None:
        try:
            from aura_cli.core.config import get_config_manager

            config = get_config_manager()
            log_level_str = config.get("log_level", "INFO").upper()
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "WARN": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }
            level = level_map.get(log_level_str, logging.INFO)
        except (ImportError, AttributeError, RuntimeError, Exception):
            level = logging.INFO

    logger = logging.getLogger(name)
    logger.setLevel(level)

    logger.handlers.clear()

    if log_to_console:
        console_handler = RichHandler(
            console=Console(stderr=True),
            show_time=True,
            show_path=False,
            rich_tracebacks=False,  # Don't show tracebacks in console (only in log file)
            tracebacks_show_locals=False,
        )
        console_handler.setLevel(logging.ERROR)  # Only show ERROR and above in console
        logger.addHandler(console_handler)

    if log_to_file:
        file_handler = _LazyDirectoryFileHandler(str(LOG_FILE))
        file_handler.setLevel(logging.DEBUG)
        file_formatter = AuraFormatter()
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger instance."""
    if name is None:
        name = "aura_cli"

    logger = logging.getLogger(name)

    if not logger.handlers:
        try:
            setup_logger(name)  # setup_logger reads config automatically
        except (ImportError, AttributeError, Exception):
            logger.setLevel(logging.INFO)
            logger.handlers.clear()
            console_handler = RichHandler(
                console=Console(stderr=True),
                show_time=True,
                show_path=False,
            )
            console_handler.setLevel(logging.ERROR)
            logger.addHandler(console_handler)
    else:
        try:
            from aura_cli.core.config import get_config_manager

            config = get_config_manager()
            log_level_str = config.get("log_level", "INFO").upper()
            level_map = {
                "DEBUG": logging.DEBUG,
                "INFO": logging.INFO,
                "WARNING": logging.WARNING,
                "WARN": logging.WARNING,
                "ERROR": logging.ERROR,
                "CRITICAL": logging.CRITICAL,
            }
            new_level = level_map.get(log_level_str, logging.INFO)
            if logger.level != new_level:
                logger.setLevel(new_level)
                for handler in logger.handlers:
                    if hasattr(handler, "setLevel"):
                        handler.setLevel(new_level)
        except (ImportError, AttributeError, Exception) as _e:
            logger.debug(f"Ignorado: {_e}")
        logger.propagate = False

    return logger
