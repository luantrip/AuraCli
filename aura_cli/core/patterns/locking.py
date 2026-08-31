"""Centralized lock management."""

import threading
from typing import Dict


class LockPool:
    """Named lock pool for coordinated resource access."""

    def __init__(self):
        self._locks: Dict[str, threading.Lock] = {}
        self._rw_locks: Dict[str, threading.RLock] = {}
        self._master = threading.Lock()

    def get(self, name: str) -> threading.Lock:
        """Get or create a named lock."""
        if name not in self._locks:
            with self._master:
                if name not in self._locks:
                    self._locks[name] = threading.Lock()
        return self._locks[name]

    def get_rlock(self, name: str) -> threading.RLock:
        """Get or create a named reentrant lock."""
        if name not in self._rw_locks:
            with self._master:
                if name not in self._rw_locks:
                    self._rw_locks[name] = threading.RLock()
        return self._rw_locks[name]


_pool = LockPool()


def get_lock(name: str) -> threading.Lock:
    """Get a named lock from the global pool."""
    return _pool.get(name)


def get_rlock(name: str) -> threading.RLock:
    """Get a named reentrant lock from the global pool."""
    return _pool.get_rlock(name)
