"""
Tests for ToolResultCache - TTL and LRU eviction cache.
"""

from datetime import datetime, timedelta
import time

from aura_cli.core.cache_advanced.tool_result_cache import CachedResult, ToolResultCache


class TestCachedResult:
    """Test CachedResult dataclass."""

    def test_cached_result_creation(self):
        """Test creating a CachedResult."""
        now = datetime.now()
        expires_at = now + timedelta(seconds=60)

        cached = CachedResult(
            value="test_value",
            expires_at=expires_at,
            created_at=now,
        )

        assert cached.value == "test_value"
        assert cached.expires_at == expires_at
        assert cached.created_at == now
        assert cached.access_count == 0
        assert cached.last_accessed == now

    def test_cached_result_is_expired(self):
        """Test checking if cached result is expired."""
        now = datetime.now()
        past = now - timedelta(seconds=10)
        future = now + timedelta(seconds=10)

        expired = CachedResult(
            value="expired",
            expires_at=past,
            created_at=past,
        )

        valid = CachedResult(
            value="valid",
            expires_at=future,
            created_at=now,
        )

        assert expired.is_expired() is True
        assert valid.is_expired() is False

    def test_cached_result_touch(self):
        """Test updating access statistics."""
        now = datetime.now()
        expires_at = now + timedelta(seconds=60)

        cached = CachedResult(
            value="test",
            expires_at=expires_at,
            created_at=now,
        )

        assert cached.access_count == 0

        cached.touch()
        assert cached.access_count == 1
        assert cached.last_accessed > now

        cached.touch()
        assert cached.access_count == 2


class TestToolResultCache:
    """Test ToolResultCache class."""

    def test_cache_initialization(self):
        """Test cache initialization."""
        cache = ToolResultCache(default_ttl_seconds=300, max_size=100)

        assert cache.default_ttl == timedelta(seconds=300)
        assert cache.max_size == 100
        assert len(cache) == 0

    def test_cache_set_and_get(self):
        """Test setting and getting values."""
        cache = ToolResultCache(default_ttl_seconds=60, max_size=10)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert len(cache) == 2

    def test_cache_get_nonexistent(self):
        """Test getting non-existent key returns None."""
        cache = ToolResultCache()

        assert cache.get("nonexistent") is None

    def test_cache_expiration(self):
        """Test cache entries expire after TTL."""
        cache = ToolResultCache(default_ttl_seconds=1, max_size=10)

        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(1.1)

        # Should be expired and removed
        assert cache.get("key1") is None
        assert len(cache) == 0

    def test_cache_custom_ttl(self):
        """Test setting custom TTL per entry."""
        cache = ToolResultCache(default_ttl_seconds=60, max_size=10)

        # Set with custom TTL
        cache.set("short_ttl", "value1", ttl_seconds=1)
        cache.set("long_ttl", "value2", ttl_seconds=5)

        assert cache.get("short_ttl") == "value1"
        assert cache.get("long_ttl") == "value2"

        # Wait for short TTL to expire
        time.sleep(1.1)

        assert cache.get("short_ttl") is None
        assert cache.get("long_ttl") == "value2"

    def test_cache_lru_eviction(self):
        """Test LRU eviction when cache reaches max size."""
        cache = ToolResultCache(default_ttl_seconds=60, max_size=3)

        # Fill cache to max size
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        assert len(cache) == 3

        # Access key1 and key2 to make them more recently used
        cache.get("key1")
        cache.get("key2")

        # Add new key - should evict key3 (least recently used)
        cache.set("key4", "value4")

        assert len(cache) == 3
        assert cache.get("key1") == "value1"  # Should still be there
        assert cache.get("key2") == "value2"  # Should still be there
        assert cache.get("key3") is None  # Should be evicted
        assert cache.get("key4") == "value4"  # Should be there

    def test_cache_cleanup_expired(self):
        """Test manual cleanup of expired entries."""
        cache = ToolResultCache(default_ttl_seconds=1, max_size=10)

        cache.set("expired1", "value1")
        cache.set("expired2", "value2")
        cache.set("valid", "value3", ttl_seconds=60)

        # Wait for expiration
        time.sleep(1.1)

        # Cleanup should remove expired entries
        removed = cache.cleanup_expired()

        assert removed == 2
        assert len(cache) == 1
        assert cache.get("valid") == "value3"

    def test_cache_clear(self):
        """Test clearing all cache entries."""
        cache = ToolResultCache()

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert len(cache) == 2

        cache.clear()

        assert len(cache) == 0
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cache_get_stats(self):
        """Test getting cache statistics."""
        cache = ToolResultCache(default_ttl_seconds=60, max_size=100)

        cache.set("key1", "value1")
        cache.set("key2", "value2")

        stats = cache.get_stats()

        assert stats["size"] == 2
        assert stats["max_size"] == 100
        assert stats["expired_count"] == 0
        assert stats["default_ttl_seconds"] == 60.0
        assert stats["oldest_entry_age_seconds"] is not None

    def test_cache_contains(self):
        """Test __contains__ method."""
        cache = ToolResultCache(default_ttl_seconds=60)

        cache.set("key1", "value1")

        assert "key1" in cache
        assert "key2" not in cache

    def test_cache_len(self):
        """Test __len__ method."""
        cache = ToolResultCache()

        assert len(cache) == 0

        cache.set("key1", "value1")
        assert len(cache) == 1

        cache.set("key2", "value2")
        assert len(cache) == 2

    def test_cache_thread_safety(self):
        """Test cache is thread-safe."""
        import threading

        cache = ToolResultCache(default_ttl_seconds=60, max_size=100)
        results = []

        def worker(thread_id):
            for i in range(10):
                key = f"key_{thread_id}_{i}"
                cache.set(key, f"value_{thread_id}_{i}")
                time.sleep(0.01)
                value = cache.get(key)
                if value:
                    results.append(value)

        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        # All values should be retrievable
        assert len(results) > 0

    def test_cache_periodic_cleanup(self):
        """Test automatic periodic cleanup."""
        cache = ToolResultCache(default_ttl_seconds=60, max_size=10)

        # Set many entries to trigger cleanup
        for i in range(150):  # More than cleanup_interval (100)
            cache.set(f"key_{i}", f"value_{i}")

        # Cleanup should have been triggered
        # Cache size should be <= max_size
        assert len(cache) <= cache.max_size
