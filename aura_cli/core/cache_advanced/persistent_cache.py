"""Auxiliary persistent disk cache.

Provides simple cache persistence for specialised use cases.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import threading
from typing import Any, Dict, Optional
import zlib

from aura_cli.core.logger import get_logger
from aura_cli.core.paths import aura_path

logger = get_logger(__name__)


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    file_hash: str
    created_at: str
    expires_at: str
    size: int
    compressed: bool = False
    access_count: int = 0
    last_accessed: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "file_hash": self.file_hash,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "size": self.size,
            "compressed": self.compressed,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "CacheEntry":
        """Create cache entry from dictionary."""
        return cls(**data)


class PersistentCache:
    """Persistent disk-backed cache with TTL and size limits."""

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_size_mb: int = 100,
        compress: bool = True,
        name: str = "default",
    ):
        """Initialise the persistent cache."""
        if cache_dir:
            self.cache_dir = Path(cache_dir)
        else:
            self.cache_dir = aura_path("cache", name)

        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.compress = compress
        self.name = name

        self.index_file = self.cache_dir / "index.json"
        self.lock = threading.RLock()
        self.index: Dict[str, CacheEntry] = {}

        self.hits = 0
        self.misses = 0

        self._load_index()
        self._cleanup_expired()

        logger.info(
            f"PersistentCache '{name}' initialized: "
            f"{len(self.index)} entradas, {self._get_total_size() / 1024 / 1024:.1f}MB"
        )

    def _load_index(self):
        """Load the cache index from disk."""
        if self.index_file.exists():
            try:
                with open(self.index_file, encoding="utf-8") as f:
                    data = json.load(f)

                self.index = {k: CacheEntry.from_dict(v) for k, v in data.items()}
            except Exception as e:
                logger.warning(f"Error loading cache index: {e}")
                self.index = {}

    def _save_index(self):
        """Persist the cache index to disk."""
        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                data = {k: v.to_dict() for k, v in self.index.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cache index: {e}")

    def _get_cache_path(self, file_hash: str) -> Path:
        """Return the cache file path for a key."""
        return self.cache_dir / f"{file_hash}.cache"

    def _generate_key_hash(self, key: str) -> str:
        """Generate a stable hash key for a cache entry."""
        return hashlib.md5(key.encode(), usedforsecurity=False).hexdigest()

    def _get_total_size(self) -> int:
        """Return total cache size in bytes."""
        return sum(entry.size for entry in self.index.values())

    def _is_expired(self, entry: CacheEntry) -> bool:
        """Return True if the cache entry has expired."""
        expires_at = datetime.fromisoformat(entry.expires_at)
        return datetime.now() > expires_at

    def _cleanup_expired(self):
        """Remove expired entries from the cache."""
        with self.lock:
            expired_keys = [
                key for key, entry in self.index.items() if self._is_expired(entry)
            ]

            for key in expired_keys:
                self._delete_entry(key)

            if expired_keys:
                logger.debug(
                    f"Removidas {len(expired_keys)} entradas expiradas do cache"
                )

    def _delete_entry(self, key: str):
        """Delete a cache entry without acquiring a lock."""
        if key in self.index:
            entry = self.index[key]
            cache_file = self._get_cache_path(entry.file_hash)

            if cache_file.exists():
                try:
                    cache_file.unlink()
                except Exception as e:
                    logger.warning(f"Error removing cache file: {e}")

            del self.index[key]

    def _cleanup_if_needed(self):
        """Remove old entries if the cache exceeds its size limit."""
        with self.lock:
            total_size = self._get_total_size()

            if total_size <= self.max_size_bytes:
                return

            # Sort by last access (LRU)
            sorted_keys = sorted(
                self.index.keys(),
                key=lambda k: self.index[k].last_accessed or self.index[k].created_at,
            )

            target_size = int(self.max_size_bytes * 0.8)
            removed_count = 0

            while total_size > target_size and sorted_keys:
                oldest_key = sorted_keys.pop(0)
                total_size -= self.index[oldest_key].size
                self._delete_entry(oldest_key)
                removed_count += 1

            if removed_count > 0:
                self._save_index()
                logger.info(f"Cache cleanup: {removed_count} entradas removidas (LRU)")

    def get(self, key: str) -> Optional[Any]:
        """Get a cached value by key. Returns None if missing or expired."""
        with self.lock:
            if key not in self.index:
                self.misses += 1
                return None

            entry = self.index[key]

            if self._is_expired(entry):
                self._delete_entry(key)
                self._save_index()
                self.misses += 1
                return None

            # Carregar do disco
            cache_file = self._get_cache_path(entry.file_hash)
            if not cache_file.exists():
                self._delete_entry(key)
                self._save_index()
                self.misses += 1
                return None

            try:
                with open(cache_file, "rb") as f:
                    data = f.read()

                # Decompress if needed
                if entry.compressed:
                    data = zlib.decompress(data)

                value = json.loads(data.decode("utf-8"))

                # Update access statistics
                entry.access_count += 1
                entry.last_accessed = datetime.now().isoformat()
                self._save_index()

                self.hits += 1
                logger.debug(f"Cache hit: {key}")
                return value

            except Exception as e:
                logger.error(f"Error reading cache: {e}")
                self._delete_entry(key)
                self._save_index()
                self.misses += 1
                return None

    def set(self, key: str, value: Any, ttl: int = 3600):
        """Store a value in the cache."""
        with self.lock:
            file_hash = self._generate_key_hash(key)
            cache_file = self._get_cache_path(file_hash)

            try:
                data = json.dumps(
                    value,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")

                # Comprimir se habilitado
                compressed = False
                if self.compress and len(data) > 1024:  # Only compress if > 1KB
                    compressed_data = zlib.compress(data, level=6)
                    if (
                        len(compressed_data) < len(data) * 0.9
                    ):  # Only use if saving > 10%
                        data = compressed_data
                        compressed = True

                # Salvar no disco
                with open(cache_file, "wb") as f:
                    f.write(data)

                now = datetime.now()
                entry = CacheEntry(
                    file_hash=file_hash,
                    created_at=now.isoformat(),
                    expires_at=(now + timedelta(seconds=ttl)).isoformat(),
                    size=len(data),
                    compressed=compressed,
                    access_count=0,
                    last_accessed=None,
                )

                if key in self.index:
                    old_file = self._get_cache_path(self.index[key].file_hash)
                    if old_file.exists() and old_file != cache_file:
                        old_file.unlink()

                self.index[key] = entry
                self._save_index()

                logger.debug(
                    f"Cache set: {key} ({len(data)} bytes, compressed={compressed})"
                )

                # Evict if needed
                self._cleanup_if_needed()

            except Exception as e:
                logger.error(f"Error saving to cache: {e}")

    def delete(self, key: str) -> bool:
        """Delete a cache entry. Returns True if found."""
        with self.lock:
            if key not in self.index:
                return False

            self._delete_entry(key)
            self._save_index()
            return True

    def clear(self) -> int:
        """Clear the entire cache and return the number of entries removed."""
        with self.lock:
            count = len(self.index)

            for entry in self.index.values():
                cache_file = self._get_cache_path(entry.file_hash)
                if cache_file.exists():
                    cache_file.unlink()

            self.index.clear()
            self._save_index()

            logger.info(f"Cache limpo: {count} entradas removidas")
            return count

    def get_stats(self) -> Dict[str, Any]:
        """Return cache statistics as a dict."""
        with self.lock:
            total_size = self._get_total_size()
            hit_rate = (
                self.hits / (self.hits + self.misses)
                if (self.hits + self.misses) > 0
                else 0
            )

            return {
                "name": self.name,
                "entries": len(self.index),
                "size_bytes": total_size,
                "size_mb": round(total_size / 1024 / 1024, 2),
                "max_size_mb": self.max_size_bytes / 1024 / 1024,
                "utilization": round(total_size / self.max_size_bytes * 100, 1),
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(hit_rate * 100, 1),
                "compression_enabled": self.compress,
            }

    def contains(self, key: str) -> bool:
        """Return True if the key exists and has not expired."""
        with self.lock:
            if key not in self.index:
                return False
            return not self._is_expired(self.index[key])


_persistent_cache: Optional[PersistentCache] = None


def get_persistent_cache() -> PersistentCache:
    """Return the global persistent cache singleton."""
    global _persistent_cache
    if _persistent_cache is None:
        _persistent_cache = PersistentCache(name="global")
    return _persistent_cache
