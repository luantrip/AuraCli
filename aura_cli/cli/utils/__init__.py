"""Utility modules for Aura CLI.

Provides shared utilities for thread management, error handling, worker factories,
and common operations.
"""

import logging
import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from aura_cli.cli.utils.thread_manager import ThreadManager

logger = logging.getLogger(__name__)


# Import from parent utils module
def clear_screen() -> None:
    """Clear screen like Command+K on Mac (clears screen but keeps scroll history)."""
    import os
    import sys

    if os.name == "nt":
        import subprocess

        subprocess.run(["cls"], shell=False, check=False)
    else:
        # Unix/Mac: use ANSI escape codes like Command+K
        # \033[2J - Clear entire screen
        # \033[H - Move cursor to top-left corner
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def set_environment_for_litellm() -> None:
    """Set environment variables for LiteLLM from secure config or fallback sources."""

    # Collect keys from all sources before modifying env
    keys_to_set: dict = {}

    # Source 1: secure config (keyring)
    try:
        from aura_cli.core.secure_config import secure_config_manager

        for provider, env_name in [
            ("google", "GOOGLE_API_KEY"),
            ("openai", "OPENAI_API_KEY"),
            ("anthropic", "ANTHROPIC_API_KEY"),
            ("nvidia", "NVIDIA_API_KEY"),
            ("openrouter", "OPENROUTER_API_KEY"),
            ("groq", "GROQ_API_KEY"),
        ]:
            val = secure_config_manager.get_api_key(provider)
            if val:
                keys_to_set[env_name] = val
    except Exception as _e:
        logger.debug("SecureConfig unavailable in subagent key setup: %s", _e)

    # Source 2: get_api_keys_dict (reads from config file + env)
    try:
        from aura_cli.cli.helpers import get_api_keys_dict

        api_keys = get_api_keys_dict()
        for env_name in [
            "GOOGLE_API_KEY",
            "GEMINI_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "NVIDIA_API_KEY",
            "OPENROUTER_API_KEY",
            "GROQ_API_KEY",
        ]:
            if env_name not in keys_to_set and api_keys.get(env_name):
                keys_to_set[env_name] = api_keys[env_name]
    except Exception as _e:
        logger.debug("get_api_keys_dict unavailable in subagent key setup: %s", _e)

    # Now set all collected keys in environment
    for env_name, value in keys_to_set.items():
        os.environ[env_name] = value

    # Ensure GEMINI_API_KEY alias is set if GOOGLE_API_KEY exists
    if "GOOGLE_API_KEY" in keys_to_set and "GEMINI_API_KEY" not in os.environ:
        os.environ["GEMINI_API_KEY"] = keys_to_set["GOOGLE_API_KEY"]
    elif "GEMINI_API_KEY" in keys_to_set and "GOOGLE_API_KEY" not in os.environ:
        os.environ["GOOGLE_API_KEY"] = keys_to_set["GEMINI_API_KEY"]


def __getattr__(name: str) -> Any:
    """Preserve utility re-exports without importing the worker stack eagerly."""
    if name in {"ThreadManager", "get_thread_manager"}:
        from aura_cli.cli.utils import thread_manager

        return getattr(thread_manager, name)
    if name in {"create_agi_worker_thread", "create_ops_worker_thread"}:
        from aura_cli.cli.utils import worker_factory

        return getattr(worker_factory, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "ThreadManager",
    "clear_screen",
    "create_agi_worker_thread",
    "create_ops_worker_thread",
    "get_thread_manager",
    "set_environment_for_litellm",
]
