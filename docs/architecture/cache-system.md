# 💾 Cache Guide - Advanced Caching System

Aura CLI provides a sophisticated multi-level caching system to improve performance and reduce redundant operations.

---

## 📋 Overview

The cache system includes:
- **Persistent Cache**: Disk-based cache that survives restarts
- **Analysis Cache**: Specialized cache for code analysis results
- **Embedding Cache**: Cache for vector embeddings
- **LRU Policy**: Automatic cleanup of least recently used entries
- **TTL Support**: Time-to-live for cache entries
- **Compression**: Optional compression to save disk space

---

## 🎯 Cache Types

### Persistent Cache

General-purpose disk cache for any data:

```python
from aura_cli.core.cache_advanced import get_persistent_cache

cache = get_persistent_cache()

# Store data with TTL
cache.set("my_key", {"data": "value"}, ttl=3600)  # 1 hour

# Retrieve data
data = cache.get("my_key")

# Check if exists
if cache.contains("my_key"):
    print("Cached!")
```

**Features:**
- Disk persistence (survives restarts)
- Configurable TTL per entry
- LRU cleanup when size limit reached
- Optional compression
- Thread-safe operations

### Analysis Cache

Specialized cache for code analysis results:

```python
from aura_cli.core.cache_advanced import get_analysis_cache

cache = get_analysis_cache()

# Cache analysis result
cache.set("file_hash", {
    "issues": [...],
    "complexity": 15,
    "metrics": {...}
}, ttl=86400)  # 24 hours

# Retrieve
result = cache.get("file_hash")
```

**Features:**
- Optimized for code analysis data
- Automatic file hash generation
- Longer default TTL (24 hours)

### Embedding Cache

Cache for vector embeddings:

```python
from aura_cli.core.cache_advanced import get_embedding_cache

cache = get_embedding_cache()

# Cache embedding
cache.set("text_hash", embedding_vector, ttl=604800)  # 7 days

# Retrieve
embedding = cache.get("text_hash")
```

**Features:**
- Optimized for vector data
- Very long TTL (embeddings don't change)
- Efficient storage format

---

## ⚙️ Configuration

### Cache Settings

Caches are configured with:

```python
from aura_cli.core.cache_advanced import PersistentCache

cache = PersistentCache(
    cache_dir=Path.home() / ".aura" / "cache" / "custom",
    max_size_mb=200,  # 200 MB limit
    compress=True,    # Enable compression
    name="custom"     # Cache instance name
)
```

**Parameters:**
- `cache_dir`: Storage directory (default: `~/.aura/cache/{name}`)
- `max_size_mb`: Maximum size in megabytes (default: 100)
- `compress`: Enable zlib compression (default: True)
- `name`: Cache instance name

### Default Locations

- Persistent Cache: `~/.aura/cache/global/`
- Analysis Cache: `~/.aura/cache/analysis/`
- Embedding Cache: `~/.aura/cache/embeddings/`

---

## 🔧 Cache Operations

### Setting Values

```python
cache.set(
    key="my_key",
    value={"data": "value"},
    ttl=3600  # Seconds until expiration
)
```

### Getting Values

```python
value = cache.get("my_key")
if value is None:
    # Cache miss - value doesn't exist or expired
    pass
```

### Checking Existence

```python
if cache.contains("my_key"):
    # Key exists and not expired
    value = cache.get("my_key")
```

### Clearing Cache

```python
# Clear all entries
count = cache.clear()
print(f"Cleared {count} entries")

# Clear specific cache via CLI
# /cache clear persistent
# /cache clear analysis
# /cache clear embedding
# /cache clear  # Clear all
```

---

## 📊 Cache Statistics

### Via CLI

```bash
› /cache stats
```

Shows:
- Number of entries
- Total size (MB)
- Hit/miss counts
- Hit rate percentage
- Compression status

### Via API

```python
stats = cache.get_stats()

print(f"Entries: {stats['entries']}")
print(f"Size: {stats['size_mb']} MB")
print(f"Hit Rate: {stats['hit_rate']}%")
print(f"Hits: {stats['hits']}")
print(f"Misses: {stats['misses']}")
```

---

## 🧹 Cache Management

### Automatic Cleanup

Caches automatically clean up:
1. **Expired entries**: Removed when accessed after TTL
2. **LRU cleanup**: When size limit reached, least recently used entries are removed
3. **Startup cleanup**: Expired entries removed on initialization

### Manual Cleanup

```bash
# Clear specific cache
› /cache clear persistent
› /cache clear analysis
› /cache clear embedding

# Clear all caches
› /cache clear
```

### Cache Size Limits

Default limits:
- Persistent Cache: 100 MB
- Analysis Cache: 50 MB
- Embedding Cache: 200 MB

When limit reached, LRU policy removes oldest entries until under 80% of limit.

---

## 💡 Best Practices

### TTL Selection

Choose appropriate TTL based on data volatility:

```python
# Frequently changing data
cache.set("user_data", data, ttl=300)  # 5 minutes

# Stable data
cache.set("config", config, ttl=3600)  # 1 hour

# Very stable data
cache.set("embeddings", emb, ttl=604800)  # 7 days
```

### Key Naming

Use descriptive, unique keys:

```python
# Good
cache.set(f"analysis:{file_hash}", result)
cache.set(f"embedding:{text_hash}", embedding)

# Bad
cache.set("data", result)  # Too generic
```

### Cache Warming

Pre-populate cache for better performance:

```python
# Warm cache on startup
for file in important_files:
    if not cache.contains(file_hash):
        result = analyze_file(file)
        cache.set(file_hash, result)
```

### Error Handling

```python
try:
    value = cache.get(key)
    if value is None:
        # Cache miss - compute value
        value = expensive_operation()
        cache.set(key, value, ttl=3600)
except Exception as e:
    # Cache error - fallback to direct computation
    logger.warning(f"Cache error: {e}")
    value = expensive_operation()
```

---

## 🔍 Cache Internals

### Storage Format

Caches store data as:
- **Index file**: `index.json` with metadata
- **Data files**: `{hash}.cache` with actual data
- **Compression**: Optional zlib compression

### Thread Safety

All cache operations are thread-safe using `RLock`:
- Multiple threads can read simultaneously
- Writes are exclusive
- No race conditions

### Performance

- **Memory index**: Fast lookups without disk access
- **Lazy loading**: Data loaded from disk only when accessed
- **Batch operations**: Multiple operations batched for efficiency

---

## 📝 Examples

### Caching Code Analysis

```python
from aura_cli.core.cache_advanced import get_analysis_cache
import hashlib

cache = get_analysis_cache()

def analyze_with_cache(file_path: str):
    # Generate cache key from file hash
    with open(file_path, 'rb') as f:
        file_hash = hashlib.md5(f.read()).hexdigest()
    
    # Check cache
    result = cache.get(file_hash)
    if result:
        return result
    
    # Cache miss - perform analysis
    result = perform_analysis(file_path)
    
    # Cache result
    cache.set(file_hash, result, ttl=86400)  # 24 hours
    
    return result
```

### Caching Embeddings

```python
from aura_cli.core.cache_advanced import get_embedding_cache
import hashlib

cache = get_embedding_cache()

def get_embedding_with_cache(text: str):
    # Generate cache key
    text_hash = hashlib.md5(text.encode()).hexdigest()
    
    # Check cache
    embedding = cache.get(text_hash)
    if embedding is not None:
        return embedding
    
    # Cache miss - generate embedding
    embedding = generate_embedding(text)
    
    # Cache with long TTL (embeddings don't change)
    cache.set(text_hash, embedding, ttl=604800)  # 7 days
    
    return embedding
```

### Custom Cache Instance

```python
from aura_cli.core.cache_advanced import PersistentCache
from pathlib import Path

# Create custom cache
custom_cache = PersistentCache(
    cache_dir=Path.home() / ".myapp" / "cache",
    max_size_mb=500,
    compress=True,
    name="myapp"
)

# Use it
custom_cache.set("key", "value", ttl=3600)
value = custom_cache.get("key")
```

---

## 🔗 Related Documentation

- [Quick Start](../user-guides/quick-start.md) - Getting started
- [Configuration](../user-guides/configuration.md) - Configuration guide
- [Session Management](../user-guides/sessions.md) - Session system

---

## 🐛 Troubleshooting

### Cache Not Working

1. Check cache directory exists and is writable
2. Verify cache size limits not exceeded
3. Check TTL hasn't expired
4. Review logs for cache errors

### High Disk Usage

1. Reduce `max_size_mb` for caches
2. Clear old caches: `/cache clear`
3. Enable compression (default: enabled)
4. Reduce TTL for frequently changing data

### Low Hit Rate

1. Increase TTL for stable data
2. Check cache keys are consistent
3. Verify cache is being used (not bypassed)
4. Review cache statistics: `/cache stats`

---

**Version**: 0.1.0  
**Last Updated**: 2026
