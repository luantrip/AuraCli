"""Shared, framework-neutral glyph vocabulary (CLI ↔ TUI parity source).

Both the Rich CLI (`cli/ui/constants.py::UIIcons`) and the Textual TUI
(`tui/constants.py`) must render the SAME Unicode glyph for each semantic token
listed here. This module is the single source of truth; the parity contract
(`tests/unit/test_architecture_contracts.py`) fails CI when either surface drifts.

Only tokens that carry cross-surface meaning live here. Surface-private glyphs
(decorative separators, box-drawing, surface-specific affordances) stay local to
each surface and are intentionally NOT governed.

Canonical style: "Assembly/Retro-Future" geometric set, owned by the CLI
`UIIcons` docstring. When CLI and TUI disagreed historically, the CLI value is
canonical and the TUI was realigned.
"""

from __future__ import annotations

# Semantic token -> canonical Unicode glyph.
# Keep alphabetical within each group for easy diffing.
SHARED_GLYPHS: dict[str, str] = {
    # Status
    "SUCCESS": "✔",
    "ERROR": "✖",
    "WARNING": "▲",
    "INFO": "ℹ",
    "IDLE": "○",  # empty circle = waiting (frees ⬡ for AGI; resolves collision)
    "THINKING": "⬢",  # filled hexagon = processing
    # Brand
    "AURA": "✦",
    # Agents
    "AGENT": "◈",
    "AGI": "⬡",  # hexagon = the AGI node
    "OPS": "⚡",  # high voltage = operations
    # Actions / filesystem
    "TOOL": "⚒",
    "SEARCH": "⚲",
    "EDIT": "✎",
    "CREATE": "✚",
    "RUN": "▶",
    "GIT": "ᛘ",
}


def shared_glyph(token: str) -> str:
    """Resolve a canonical glyph from the shared vocabulary.

    Raises ValueError for unknown tokens so drift is caught eagerly rather than
    silently rendering an empty string.
    """
    try:
        return SHARED_GLYPHS[token]
    except KeyError as error:
        raise ValueError(f"Unknown shared glyph token: {token}") from error


__all__ = ["SHARED_GLYPHS", "shared_glyph"]
