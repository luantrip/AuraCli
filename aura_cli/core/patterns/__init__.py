"""Reusable design patterns for Aura CLI."""

from aura_cli.core.patterns.error_handling import (
    async_handle_exceptions,
    handle_exceptions,
)
from aura_cli.core.patterns.locking import LockPool, get_lock, get_rlock
from aura_cli.core.patterns.singleton import SingletonMeta

__all__ = [
    "LockPool",
    "SingletonMeta",
    "async_handle_exceptions",
    "get_lock",
    "get_rlock",
    "handle_exceptions",
]
