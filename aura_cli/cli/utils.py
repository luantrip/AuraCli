"""
Utility functions for Aura CLI
"""

import logging
import os

from rich.console import Console

console = Console()
logger = logging.getLogger(__name__)


def clear_screen() -> None:
    """
    Clear the terminal screen like Command+K on Mac (clears screen but keeps scroll history).
    Uses ANSI escape codes for cross-platform compatibility.
    """
    import sys

    if os.name == "nt":
        console.clear()
    else:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def _set_env_key(env_key: str, value: str | None, alias: str | None = None) -> bool:
    """Set an environment variable if value is truthy. Returns True if set."""
    if value:
        os.environ[env_key] = str(value)
        if alias:
            os.environ[alias] = str(value)
        return True
    return False


def set_environment_for_litellm() -> None:
    """
    Set up environment variables for LiteLLM.
    This ensures that LiteLLM can find API keys from the config.
    Always prioritizes SecureConfig (keyring) over environment variables.

    IMPORTANT: This function sets ALL available API keys, not just the first one found.
    This allows users to use multiple LLM providers simultaneously.

    Note: This function permanently mutates the process environment.
    It is intended to be called once at startup and does not restore
    previous values. Do not call multiple times.
    """
    for key in [
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "CEREBRAS_API_KEY",
        "OPENROUTER_API_KEY",
        "GROQ_API_KEY",
    ]:
        if key in os.environ:
            del os.environ[key]

    if _try_load_from_secure_config():
        return
    if _try_load_from_helpers():
        return
    _try_load_from_legacy_config()


def _try_load_from_secure_config() -> bool:
    """Attempt to load API keys from SecureConfig (keyring). Returns True if any key was set."""
    try:
        from aura_cli.core.secure_config import secure_config_manager

        keys_loaded = False
        keys_loaded |= _set_env_key(
            "GOOGLE_API_KEY",
            secure_config_manager.get_api_key("google"),
            "GEMINI_API_KEY",
        )
        keys_loaded |= _set_env_key(
            "OPENAI_API_KEY", secure_config_manager.get_api_key("openai")
        )
        keys_loaded |= _set_env_key(
            "ANTHROPIC_API_KEY", secure_config_manager.get_api_key("anthropic")
        )
        keys_loaded |= _set_env_key(
            "NVIDIA_API_KEY", secure_config_manager.get_api_key("nvidia")
        )
        keys_loaded |= _set_env_key(
            "CEREBRAS_API_KEY", secure_config_manager.get_api_key("cerebras")
        )
        keys_loaded |= _set_env_key(
            "OPENROUTER_API_KEY", secure_config_manager.get_api_key("openrouter")
        )
        keys_loaded |= _set_env_key(
            "GROQ_API_KEY", secure_config_manager.get_api_key("groq")
        )
        # Register Gemini keys for round-robin rotation (supports comma-separated multi-key)
        google_key = secure_config_manager.get_api_key("google") or ""
        if google_key:
            try:
                from aura_cli.core.llm.key_rotation import register_keys

                register_keys("google", google_key)
            except Exception as _e:
                logger.debug("Key rotation registration skipped: %s", _e)
        return keys_loaded
    except Exception as e:
        try:
            from aura_cli.core.logger import get_logger

            get_logger(__name__).debug(
                f"Error accessing SecureConfig in set_environment_for_litellm: {e}",
                exc_info=True,
            )
        except Exception:
            import sys
            import traceback

            print(f"Error accessing SecureConfig: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
    return False


def _try_load_from_helpers() -> bool:
    """Attempt to load API keys from get_api_keys_dict fallback. Returns True if any key was set."""
    try:
        from aura_cli.cli.helpers import get_api_keys_dict

        api_keys = get_api_keys_dict()

        keys_loaded = False
        google = api_keys.get("GOOGLE_API_KEY") or api_keys.get("GEMINI_API_KEY")
        if google:
            keys_loaded |= _set_env_key("GOOGLE_API_KEY", google, "GEMINI_API_KEY")
            try:
                from aura_cli.core.llm.key_rotation import register_keys

                register_keys("google", google)
            except Exception as _e:
                logger.debug("Key rotation registration skipped: %s", _e)
        if "OPENAI_API_KEY" not in os.environ:
            keys_loaded |= _set_env_key(
                "OPENAI_API_KEY", api_keys.get("OPENAI_API_KEY")
            )
        if "ANTHROPIC_API_KEY" not in os.environ:
            keys_loaded |= _set_env_key(
                "ANTHROPIC_API_KEY", api_keys.get("ANTHROPIC_API_KEY")
            )
        if "NVIDIA_API_KEY" not in os.environ:
            keys_loaded |= _set_env_key(
                "NVIDIA_API_KEY", api_keys.get("NVIDIA_API_KEY")
            )
        if "CEREBRAS_API_KEY" not in os.environ:
            keys_loaded |= _set_env_key(
                "CEREBRAS_API_KEY", api_keys.get("CEREBRAS_API_KEY")
            )
        if "OPENROUTER_API_KEY" not in os.environ:
            keys_loaded |= _set_env_key(
                "OPENROUTER_API_KEY", api_keys.get("OPENROUTER_API_KEY")
            )
        if "GROQ_API_KEY" not in os.environ:
            keys_loaded |= _set_env_key("GROQ_API_KEY", api_keys.get("GROQ_API_KEY"))
        return keys_loaded
    except Exception as _e:
        logger.debug("Failed to load API keys from SecureConfig: %s", _e)
    return False


def _try_load_from_legacy_config() -> None:
    """Attempt to load API keys from legacy config format (last resort)."""
    try:
        from aura_cli.core.config import get_config_manager

        config = get_config_manager()
        old_keys = config.get("api_keys") or {}

        _set_env_key("GOOGLE_API_KEY", old_keys.get("google_api_key"), "GEMINI_API_KEY")
        if "OPENAI_API_KEY" not in os.environ:
            _set_env_key("OPENAI_API_KEY", old_keys.get("openai_api_key"))
        if "ANTHROPIC_API_KEY" not in os.environ:
            _set_env_key("ANTHROPIC_API_KEY", old_keys.get("anthropic_api_key"))
        if "CEREBRAS_API_KEY" not in os.environ:
            _set_env_key("CEREBRAS_API_KEY", old_keys.get("cerebras_api_key"))
        if "OPENROUTER_API_KEY" not in os.environ:
            _set_env_key("OPENROUTER_API_KEY", old_keys.get("openrouter_api_key"))
        if "GROQ_API_KEY" not in os.environ:
            _set_env_key("GROQ_API_KEY", old_keys.get("groq_api_key"))
    except Exception as _e:
        logger.debug("Failed to load API keys from legacy config: %s", _e)
