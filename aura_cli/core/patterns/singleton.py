"""Thread-safe Singleton base class."""

import threading
from typing import ClassVar


class SingletonMeta(type):
    """Metaclass for thread-safe singletons."""

    _instances: ClassVar[dict] = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                if cls not in cls._instances:
                    cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

    @classmethod
    def reset(mcs, cls):
        """Reset singleton instance (for testing)."""
        with mcs._lock:
            mcs._instances.pop(cls, None)
