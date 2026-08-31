"""CLI slash commands — thin derivation over the shared command catalog.

Descriptions and subcommands come from the single source of truth in
``aura_cli.application.commands`` (catalog). This module only adds CLI-specific
argument *value* completions (e.g. provider names for ``/model``, theme names for
``/theme``) that the catalog does not model.
"""

from __future__ import annotations

from typing import Dict, List

from aura_cli.application.commands import (
    command_dict_for_autocomplete,
    slash_command_pairs,
)


def get_cli_command_descriptions() -> Dict[str, str]:
    """All slash command descriptions for prompt_toolkit completer (PT).

    Derived entirely from the catalog to avoid divergent duplicate text.
    """
    return dict(slash_command_pairs("pt"))


# CLI-specific argument *value* completions that are not subcommands (and thus are
# not part of the catalog). Kept here because they are a CLI-completer concern.
_CLI_ARG_VALUES: Dict[str, List[str]] = {
    "/theme": [
        "aura_minimal",
        "cyberpunk",
        "nebula",
        "holographic",
        "dark",
        "light",
        "mono",
    ],
    "/ops": ["git", "docker", "general"],
    "/dev": ["status"],
    "/auto": ["on", "off", "status"],
    "/model": ["gemini", "gpt", "claude", "openrouter", "auto", "nvidia", "cerebras", "groq"],
    "/tools": ["audit"],
}


def get_cli_command_args() -> Dict[str, List[str]]:
    """Subcommand/argument completions for contextual completion.

    Subcommands are sourced from the catalog (single source of truth); CLI-specific
    argument value completions are merged on top.
    """
    catalog = command_dict_for_autocomplete("pt")
    args: Dict[str, List[str]] = {
        name: list(entry["subcommands"])
        for name, entry in catalog.items()
        if entry["subcommands"]
    }
    # Merge CLI-specific arg values on top of catalog subcommands (append any that
    # are not already present), preserving both concepts for the completer.
    for name, values in _CLI_ARG_VALUES.items():
        existing = args.setdefault(name, [])
        for value in values:
            if value not in existing:
                existing.append(value)
    return args


def get_cli_command_prefixes() -> Dict[str, Dict[str, str]]:
    """Short prefixes for argument completion."""
    return {
        "/theme": {
            "a": "aura_minimal",
            "c": "cyberpunk",
            "n": "nebula",
            "h": "holographic",
            "d": "dark",
            "l": "light",
            "mo": "mono",
        },
        "/ops": {"g": "git", "d": "docker", "ge": "general"},
        "/dev": {"o": "on", "of": "off", "s": "status"},
        "/auto": {"o": "on", "of": "off", "s": "status"},
        "/model": {
            "g": "gemini",
            "gp": "gpt",
            "c": "claude",
            "o": "openrouter",
            "a": "auto",
            "n": "nvidia",
        },
        "/session": {
            "s": "save",
            "l": "load",
            "li": "list",
            "d": "delete",
            "i": "info",
        },
        "/resume": {},
        "/workflow": {
            "c": "create",
            "r": "run",
            "l": "list",
            "d": "delete",
            "i": "info",
        },
        "/cache": {"s": "stats", "c": "clear"},
        "/checkpoint": {
            "i": "init",
            "c": "create",
            "l": "list",
            "r": "restore",
            "h": "hard",
        },
        "/tangent": {"t": "tail"},
    }
