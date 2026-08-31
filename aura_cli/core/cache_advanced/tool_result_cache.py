"""
Tool Result Cache with TTL and LRU Eviction.

Provides a cache implementation specifically for tool execution results
with time-to-live (TTL) and least-recently-used (LRU) eviction policies.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from typing import Any, Dict, Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class CachedResult:
    """Cached result with expiration timestamp."""

    value: Any
    expires_at: datetime
    created_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    def __post_init__(self):
        """Initialize last_accessed if not set."""
        if self.last_accessed is None:
            self.last_accessed = self.created_at

    def is_expired(self) -> bool:
        """Check if cached result is expired."""
        return datetime.now() > self.expires_at

    def touch(self):
        """Update access statistics."""
        self.access_count += 1
        self.last_accessed = datetime.now()


class ToolResultCache:
    """Cache for tool results with TTL and LRU eviction.

    Features:
        - Time-to-live (TTL) for automatic expiration
        - LRU eviction when cache reaches max size
        - Thread-safe operations
        - Access statistics tracking
        - Automatic cleanup of expired entries

    Attributes:
        default_ttl_seconds: Default TTL in seconds (default: 300 = 5 minutes)
        max_size: Maximum number of cached entries (default: 1000)
        _cache: Internal cache dictionary
        _lock: Thread lock for thread-safe operations
    """

    def __init__(self, default_ttl_seconds: int = 300, max_size: int = 1000) -> None:
        """Initialize tool result cache.

        Args:
            default_ttl_seconds: Default TTL in seconds (default: 300)
            max_size: Maximum number of cached entries (default: 1000)
        """
        self.default_ttl = timedelta(seconds=default_ttl_seconds)
        self.max_size = max_size
        self._cache: Dict[str, CachedResult] = {}
        self._lock = threading.RLock()
        self._cleanup_counter = 0
        self._cleanup_interval = 100  # Cleanup every 100 operations

        logger.debug(
            f"ToolResultCache initialized: TTL={default_ttl_seconds}s, max_size={max_size}"
        )

    def get(self, key: str) -> Optional[Any]:
        """Get cached value if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value if found and not expired, None otherwise
        """
        with self._lock:
            if key not in self._cache:
                return None

            cached = self._cache[key]

            if cached.is_expired():
                del self._cache[key]
                logger.debug(f"Cache entry '{key}' expired and removed")
                return None

            cached.touch()
            return cached.value

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """Set cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Optional TTL override (uses default if None)
        """
        with self._lock:
            if len(self._cache) >= self.max_size and key not in self._cache:
                self._evict_oldest()

            ttl = (
                timedelta(seconds=ttl_seconds)
                if ttl_seconds is not None
                else self.default_ttl
            )
            expires_at = datetime.now() + ttl

            self._cache[key] = CachedResult(
                value=value,
                expires_at=expires_at,
                created_at=datetime.now(),
            )

            self._cleanup_counter += 1
            if self._cleanup_counter >= self._cleanup_interval:
                self._cleanup_counter = 0
                self.cleanup_expired()

    def _evict_oldest(self) -> None:
        """Evict oldest entry using LRU policy.

        Removes the entry that was least recently accessed.
        If multiple entries have the same last_accessed time,
        removes the one with the lowest access_count.
        """
        if not self._cache:
            return

        oldest_key = min(
            self._cache.keys(),
            key=lambda k: (
                self._cache[k].last_accessed,
                -self._cache[k].access_count,  # Prefer entries with fewer accesses
            ),
        )

        del self._cache[oldest_key]
        logger.debug(f"LRU eviction: removed '{oldest_key}'")

    def cleanup_expired(self) -> int:
        """Remove expired entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            now = datetime.now()
            expired_keys = [k for k, v in self._cache.items() if now > v.expires_at]

            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")

            return len(expired_keys)

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            logger.debug(f"Cache cleared: {count} entries removed")

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache statistics:
                - size: Current number of entries
                - max_size: Maximum number of entries
                - hit_rate: Estimated hit rate (if tracking enabled)
                - oldest_entry: Age of oldest entry in seconds
                - expired_count: Number of expired entries (if any)
        """
        with self._lock:
            now = datetime.now()
            expired_count = sum(1 for v in self._cache.values() if v.is_expired())

            oldest_age = None
            if self._cache:
                oldest_entry = min(self._cache.values(), key=lambda v: v.created_at)
                oldest_age = (now - oldest_entry.created_at).total_seconds()

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "expired_count": expired_count,
                "oldest_entry_age_seconds": oldest_age,
                "default_ttl_seconds": self.default_ttl.total_seconds(),
            }

    def __len__(self) -> int:
        """Return number of cached entries."""
        return len(self._cache)

    def __contains__(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        return self.get(key) is not None
