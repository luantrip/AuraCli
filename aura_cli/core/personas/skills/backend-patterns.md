---
name: backend-patterns
description: Use this skill when implementing APIs, database access, caching, authentication, service layers, or any server-side logic. Covers RESTful design, repository pattern, service layer, N+1 prevention, transactions, retry with backoff, rate limiting, and structured logging in Python.
version: 1.0.0
author: Aura Core Team
---

# Backend Development Patterns

Backend architecture patterns and best practices for scalable server-side Python applications.

## API Design Patterns

### RESTful Structure

```python
# ✅ Resource-based URLs
GET    /api/items                 # List resources
GET    /api/items/{id}            # Get single resource
POST   /api/items                 # Create resource
PUT    /api/items/{id}            # Replace resource
PATCH  /api/items/{id}            # Partial update
DELETE /api/items/{id}            # Delete resource

# ✅ Query params for filtering, sorting, pagination
GET /api/items?status=active&sort=created_at&limit=20&offset=0
```

### Repository Pattern

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional

T = TypeVar("T")

class Repository(ABC, Generic[T]):
    @abstractmethod
    async def find_all(self, filters: dict | None = None) -> list[T]: ...
    @abstractmethod
    async def find_by_id(self, id: str) -> Optional[T]: ...
    @abstractmethod
    async def create(self, data: dict) -> T: ...
    @abstractmethod
    async def update(self, id: str, data: dict) -> T: ...
    @abstractmethod
    async def delete(self, id: str) -> None: ...
```

### Service Layer Pattern

```python
class ItemService:
    def __init__(self, item_repo: ItemRepository):
        self._repo = item_repo

    async def search(self, query: str, limit: int = 10) -> list[Item]:
        # Business logic separated from data access
        embedding = await generate_embedding(query)
        results = await self._repo.vector_search(embedding, limit)
        return results[:limit]
```

## Database Patterns

### Query Optimization

```python
# ✅ Select only needed columns
cursor.execute("SELECT id, name, status FROM items WHERE status = ?", ("active",))

# ❌ Never select everything unless required
cursor.execute("SELECT * FROM items")
```

### N+1 Prevention

```python
# ❌ N+1 queries
for item in items:
    item.creator = await get_user(item.creator_id)  # N queries!

# ✅ Batch fetch
creator_ids = list({item.creator_id for item in items})
creators = await get_users_batch(creator_ids)  # 1 query
creator_map = {c.id: c for c in creators}
for item in items:
    item.creator = creator_map.get(item.creator_id)
```

### Transactions

```python
async def create_order_with_payment(order_data: dict, payment_data: dict):
    async with db.transaction():
        order = await order_repo.create(order_data)
        payment = await payment_repo.create({**payment_data, "order_id": order.id})
        return order, payment
```

## Caching — Cache-Aside Pattern

```python
async def get_item_with_cache(item_id: str) -> Item:
    cache_key = f"item:{item_id}"
    cached = await cache.get(cache_key)
    if cached:
        return Item(**json.loads(cached))
    item = await item_repo.find_by_id(item_id)
    if not item:
        raise ValueError(f"Item {item_id} not found")
    await cache.setex(cache_key, 300, json.dumps(item.__dict__))
    return item
```

## Error Handling

### Centralized Error Handler

```python
class ApiError(Exception):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)

def error_response(error: Exception) -> tuple[dict, int]:
    if isinstance(error, ApiError):
        return {"success": False, "error": error.message}, error.status_code
    if isinstance(error, ValidationError):
        return {"success": False, "error": "Validation failed", "details": str(error)}, 400
    logger.error("Unexpected error: %s", error, exc_info=True)
    return {"success": False, "error": "Internal server error"}, 500
```

### Retry with Exponential Backoff

```python
import asyncio

async def fetch_with_retry(fn, max_retries: int = 3):
    last_error = None
    for i in range(max_retries):
        try:
            return await fn()
        except Exception as e:
            last_error = e
            if i < max_retries - 1:
                await asyncio.sleep(2 ** i)  # 1s, 2s, 4s
    raise last_error
```

## Authentication & Authorization

### JWT Validation

```python
import jwt
from functools import wraps

def require_auth(f):
    @wraps(f)
    async def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            raise ApiError(401, "Missing authorization token")
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            request.user = payload
        except jwt.InvalidTokenError:
            raise ApiError(401, "Invalid token")
        return await f(*args, **kwargs)
    return decorated
```

### Role-Based Access Control

```python
from enum import StrEnum

class Permission(StrEnum):
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

ROLE_PERMISSIONS = {
    "admin": {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN},
    "editor": {Permission.READ, Permission.WRITE},
    "viewer": {Permission.READ},
}

def require_permission(permission: Permission):
    def decorator(f):
        @wraps(f)
        async def decorated(*args, **kwargs):
            user_role = request.user.get("role", "viewer")
            if permission not in ROLE_PERMISSIONS.get(user_role, set()):
                raise ApiError(403, "Insufficient permissions")
            return await f(*args, **kwargs)
        return decorated
    return decorator
```

## Rate Limiting

```python
from collections import defaultdict
from time import time

class RateLimiter:
    def __init__(self):
        self._requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, identifier: str, max_requests: int, window_seconds: int) -> bool:
        now = time()
        cutoff = now - window_seconds
        self._requests[identifier] = [t for t in self._requests[identifier] if t > cutoff]
        if len(self._requests[identifier]) >= max_requests:
            return False
        self._requests[identifier].append(now)
        return True
```

## Structured Logging

```python
import json
import logging
from datetime import datetime, timezone

class StructuredLogger:
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)

    def info(self, message: str, **context):
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "info", "message": message, **context}
        self._logger.info(json.dumps(entry))

    def error(self, message: str, error: Exception | None = None, **context):
        if error:
            context["error"] = str(error)
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "level": "error", "message": message, **context}
        self._logger.error(json.dumps(entry))

logger = StructuredLogger(__name__)
logger.info("Fetching items", request_id="abc", user_id="123")
```
