"""
API Key Rotation for Aura CLI.

Provides round-robin rotation across multiple API keys for the same provider,
maximizing free-tier throughput by distributing requests across keys.

Usage:
    Configure multiple keys separated by commas in config or environment:
        GOOGLE_API_KEY=key1,key2,key3,key4

    The rotator will cycle through them in order, distributing load evenly.
"""

import itertools
import threading
from typing import Dict, Optional

_lock = threading.Lock()
_rotators: Dict[str, itertools.cycle] = {}
_key_lists: Dict[str, list] = {}


def register_keys(provider: str, keys_string: str) -> int:
    """
    Register multiple API keys for a provider from a comma-separated string.

    Args:
        provider: Provider identifier (e.g., "google", "openai")
        keys_string: Comma-separated API keys

    Returns:
        Number of keys registered
    """
    keys = [k.strip() for k in keys_string.split(",") if k.strip()]
    with _lock:
        if not keys:
            _key_lists.pop(provider, None)
            _rotators.pop(provider, None)
            return 0
        _key_lists[provider] = keys
        _rotators[provider] = itertools.cycle(keys)

    return len(keys)


def next_key(provider: str) -> Optional[str]:
    """
    Get the next API key for a provider using round-robin rotation.

    Args:
        provider: Provider identifier (e.g., "google", "openai")

    Returns:
        Next API key in rotation, or None if no keys registered
    """
    with _lock:
        rotator = _rotators.get(provider)
        if rotator is None:
            return None
        return next(rotator)


def get_key_count(provider: str) -> int:
    """Get number of registered keys for a provider."""
    return len(_key_lists.get(provider, []))


def has_multiple_keys(provider: str) -> bool:
    """Check if provider has more than one key (rotation beneficial)."""
    return len(_key_lists.get(provider, [])) > 1


def reset():
    """Reset all registered keys (for testing)."""
    with _lock:
        _rotators.clear()
        _key_lists.clear()
