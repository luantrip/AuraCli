"""Shared, framework-neutral color palette (CLI ↔ TUI parity source).

Both the Rich CLI (`cli/ui/constants.py::UIStyles._DEFAULTS`) and the Textual TUI
(`tui/constants.py::COLOR_*` fallbacks) must use the SAME base color for each
*semantic* token listed here. The parity contract
(`tests/unit/test_architecture_contracts.py`) fails CI when either surface drifts.

Scope is intentionally limited to the SEVERITY + BRAND palette — the colors that
carry cross-surface meaning (a green "success" must be green everywhere, a red
"error" red everywhere). Typographic emphasis tokens (title, label, code, body,
caption) are surface-private: a flat CLI and a richer TUI may legitimately style
headings differently, so they are NOT governed here.

These are BASE/fallback values. Both surfaces still load live colors from their
ThemeManager at runtime; the contract pins the shared starting palette so a theme
override is a deliberate, symmetric choice rather than silent drift.

Canonical source: the CLI `UIStyles._DEFAULTS`. The TUI docstring already states
it "espelha cli/ui/constants.py UIStyles"; where it had drifted, the TUI was
realigned.
"""

from __future__ import annotations

# Semantic token -> canonical base color string (Rich/Textual compatible).
SHARED_PALETTE: dict[str, str] = {
    # Brand / structural
    "primary": "cyan",
    "secondary": "blue",
    "accent": "magenta",
    "muted": "dim white",
    # Severity
    "success": "green",
    "warning": "yellow",
    "error": "red",
    "info": "blue",
}


def shared_color(token: str) -> str:
    """Resolve a canonical base color from the shared palette.

    Raises ValueError for unknown tokens so drift is caught eagerly.
    """
    try:
        return SHARED_PALETTE[token]
    except KeyError as error:
        raise ValueError(f"Unknown shared palette token: {token}") from error


__all__ = ["SHARED_PALETTE", "shared_color"]
