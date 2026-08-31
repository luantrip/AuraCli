"""In-memory LRU/TTL cache for Aura CLI.

Use @cache_result(ttl=N) to memoize expensive functions within a session.
clear_cache() / get_cache_stats() for management.

For cross-session persistence use cache_advanced (PersistentCache,
AnalysisCache, EmbeddingCache, ToolResultCache) — not this module.
"""

from datetime import datetime, timedelta
from functools import wraps
import hashlib
from typing import Any, Callable, Dict, Optional

# Lazy import do logger para evitar deadlock circular
_logger_cache = None


def _get_logger():
    """Lazy import do logger."""
    global _logger_cache
    if _logger_cache is None:
        from aura_cli.core.logger import get_logger

        _logger_cache = get_logger(__name__)
    return _logger_cache


logger = None  # Initialised lazily when needed

_cache: Dict[str, Dict[str, Any]] = {}


def _generate_key(func_name: str, *args, **kwargs) -> str:
    """Generate a unique cache key from a function name and arguments."""
    key_data = f"{func_name}:{args!s}:{sorted(kwargs.items())!s}"
    return hashlib.md5(key_data.encode(), usedforsecurity=False).hexdigest()


def cache_result(ttl: int = 3600, max_size: int = 100):
    """Decorator to cache function results."""

    def decorator(func: Callable) -> Callable:
        """Cache decorator wrapper."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            """Wrapper function."""
            cache_key = _generate_key(func.__name__, *args, **kwargs)

            if cache_key in _cache:
                cached = _cache[cache_key]
                if datetime.now() < cached["expires_at"]:
                    _get_logger().debug(f"Cache hit para {func.__name__}")
                    return cached["value"]
                else:
                    del _cache[cache_key]
                    _get_logger().debug(f"Cache expirado para {func.__name__}")

            if len(_cache) >= max_size:
                oldest_key = min(_cache.keys(), key=lambda k: _cache[k]["created_at"])
                del _cache[oldest_key]
                _get_logger().debug("Cache evicted: removed oldest item")

            result = func(*args, **kwargs)
            _cache[cache_key] = {
                "value": result,
                "created_at": datetime.now(),
                "expires_at": datetime.now() + timedelta(seconds=ttl),
            }
            _get_logger().debug(f"Resultado cacheado para {func.__name__}")
            return result

        return wrapper

    return decorator


def clear_cache(pattern: Optional[str] = None) -> int:
    """Clear the cache, optionally filtered by pattern."""
    if pattern is None:
        count = len(_cache)
        _cache.clear()
        _get_logger().info(f"Cache fully cleared: {count} items removed")
        return count

    keys_to_remove = [k for k in _cache if pattern in k]
    for key in keys_to_remove:
        del _cache[key]

    _get_logger().info(
        f"Cache cleared for pattern '{pattern}': {len(keys_to_remove)} items removed"
    )
    return len(keys_to_remove)


def get_cache_stats() -> Dict[str, Any]:
    """Return cache statistics as a dict."""
    try:
        from aura_cli.core.config import config_manager

        max_size = config_manager.get("cache_max_size", 100)
    except Exception:
        max_size = 100

    now = datetime.now()
    expired = sum(1 for v in _cache.values() if now >= v["expires_at"])
    active = len(_cache) - expired

    return {
        "total_items": len(_cache),
        "active_items": active,
        "expired_items": expired,
        "max_size": max_size,
    }
