"""CLI package for Aura CLI — interactive loop, headless mode and agent management.

Lazy-exports: ui, AgiWorker, OpsWorker, get_api_keys_dict,
handle_multiline_input and other session helpers. Presentation layer over
core, coordinating user, agents, tools and LLM via threads and queues.
"""

from importlib import import_module

_LAZY_EXPORTS = {
    "ui": ("aura_cli.cli.ui", None),
    "AgiWorker": ("aura_cli.cli.workers", "AgiWorker"),
    "OpsWorker": ("aura_cli.cli.workers", "OpsWorker"),
    "get_api_keys_dict": ("aura_cli.cli.helpers", "get_api_keys_dict"),
    "handle_multiline_input": ("aura_cli.cli.helpers", "handle_multiline_input"),
    "handle_status_updates": ("aura_cli.cli.helpers", "handle_status_updates"),
    "initialize_conversation_history": (
        "aura_cli.cli.helpers",
        "initialize_conversation_history",
    ),
    "parse_agi_command": ("aura_cli.cli.helpers", "parse_agi_command"),
    "parse_ops_command": ("aura_cli.cli.helpers", "parse_ops_command"),
    "setup_prompt_session": ("aura_cli.cli.helpers", "setup_prompt_session"),
}


def __getattr__(name: str):
    """Load public CLI helpers only when they are explicitly requested."""
    try:
        module_name, attribute_name = _LAZY_EXPORTS[name]
    except KeyError as exc:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    module = import_module(module_name)
    value = module if attribute_name is None else getattr(module, attribute_name)
    globals()[name] = value
    return value


__all__ = [
    "AgiWorker",
    "OpsWorker",
    "get_api_keys_dict",
    "handle_multiline_input",
    "handle_status_updates",
    "initialize_conversation_history",
    "parse_agi_command",
    "parse_ops_command",
    "setup_prompt_session",
    "ui",
]

# Note: 'main' is not exported from this __init__.py to avoid RuntimeWarning
# when used as entry point. Import directly from aura_cli.cli.main if needed.
