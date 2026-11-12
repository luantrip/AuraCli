"""Canonical semantic token vocabulary (the style "constitution").

This is the single, framework-neutral source of truth for WHICH semantic roles
the design system defines. Both surfaces implement this same vocabulary:

* CLI  — `cli/ui/constants.py::UIStyles` + `cli/ui/themes/*.toml` ([colors]/[styles])
* TUI  — `tui/styles/themes.py::ThemeColors` + `tui/styles/theme.tcss` ($theme-*)

Design rules this module encodes:

1. There is ONE vocabulary of semantic roles, not one per surface. A role like
   "success" or "status_thinking" means the same thing everywhere.
2. Values are surface-dependent by necessity (the CLI speaks Rich color *names*
   like "green"; the TUI speaks hex like "#10b981"). So parity is enforced on
   the SET OF ROLES, not on literal values — except the severity+brand subset,
   where a shared literal palette (`SHARED_PALETTE`, Rich names) is pinned by
   `color_palette`.
3. Every theme (CLI TOML or TUI ThemeColors) MUST define the full color role
   set. Missing a role is a drift caught by the architecture contracts.

Token groups:

* COLOR_ROLES    — brand/severity/surface/foreground semantic colors. Every
                   theme must provide these. Superset-compatible with
                   `SHARED_PALETTE` (which pins the cross-surface severity+brand
                   literals).
* STATUS_ROLES   — agent runtime status colors (idle/thinking/working/...).
* AGENT_ROLES    — per-agent accent colors (AGI/OPS/CHAT).
* CHAT_ROLES     — conversation role colors (user/assistant/system).

The glyph vocabulary lives separately in `glyph_vocabulary.py`.
"""

from __future__ import annotations

from aura_cli.application.presentation.color_palette import (
    SHARED_PALETTE,
    shared_color,
)

# Brand + severity + surface + foreground. Every theme must define each role.
# The first 8 are the pinned cross-surface palette (see SHARED_PALETTE); the rest
# are structural colors whose literal value legitimately differs per theme.
COLOR_ROLES: frozenset[str] = frozenset(
    {
        # pinned severity + brand (SHARED_PALETTE)
        "primary",
        "secondary",
        "accent",
        "muted",
        "success",
        "warning",
        "error",
        "info",
        # surfaces + foreground (value differs per theme; role is mandatory)
        "background",
        "surface",
        "foreground",
        "foreground_muted",
        "border",
    }
)

# Agent runtime status colors (CLI: UIStyles.STATUS_*; TUI: status via theme).
STATUS_ROLES: frozenset[str] = frozenset(
    {
        "status_idle",
        "status_thinking",
        "status_working",
        "status_success",
        "status_error",
        "status_warning",
    }
)

# Per-agent accent colors.
AGENT_ROLES: frozenset[str] = frozenset(
    {
        "agent_agi",
        "agent_ops",
        "agent_chat",
    }
)

# Conversation role colors.
CHAT_ROLES: frozenset[str] = frozenset(
    {
        "chat_user",
        "chat_assistant",
        "chat_system",
    }
)

# The complete semantic color vocabulary every theme must cover.
ALL_COLOR_ROLES: frozenset[str] = (
    COLOR_ROLES | STATUS_ROLES | AGENT_ROLES | CHAT_ROLES
)

# Sanity: the pinned shared palette must be a subset of the color roles.
assert set(SHARED_PALETTE).issubset(COLOR_ROLES), (
    "SHARED_PALETTE drifted from COLOR_ROLES"
)


__all__ = [
    "AGENT_ROLES",
    "ALL_COLOR_ROLES",
    "CHAT_ROLES",
    "COLOR_ROLES",
    "SHARED_PALETTE",
    "STATUS_ROLES",
    "shared_color",
]
