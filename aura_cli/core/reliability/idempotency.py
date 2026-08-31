"""Small durable idempotency store for mutating operations."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
from typing import Any


class IdempotencyStore:
    """Remember successful operation results by caller-provided key."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self._values: dict[str, Any] = {}
        self._load()

    @staticmethod
    def key(operation: str, payload: Any) -> str:
        encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
        return hashlib.sha256(f"{operation}:{encoded}".encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        with self._lock:
            return self._values.get(key)

    def put(self, key: str, value: Any) -> None:
        with self._lock:
            self._values[key] = value
            self._save()

    def execute(self, key: str, operation):
        with self._lock:
            if key in self._values:
                return self._values[key], True
            value = operation()
            self._values[key] = value
            self._save()
            return value, False

    def _load(self) -> None:
        if self.path.exists():
            self._values = json.loads(self.path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix=".idempotency-", dir=self.path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._values, handle, indent=2, sort_keys=True, default=str)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
