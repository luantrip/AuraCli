"""Deterministic layout contract for the Rich CLI surface.

The contract keeps geometry decisions out of individual renderers.  It is
pure, width-driven and safe to use in tests or non-interactive output.
"""

from __future__ import annotations

from dataclasses import dataclass

from aura_cli.application.presentation.cli_visual import CliDensity, decide_cli_visual

_MIN_WIDTH = 1
_DEFAULT_WIDTH = 80
_MAX_INLINE_RESERVE = 8


@dataclass(frozen=True)
class LayoutMetrics:
    """Geometry and density values for one terminal width."""

    width: int
    density: CliDensity
    group_padding: tuple[int, int]
    focus_padding: tuple[int, int]
    chat_padding: tuple[int, int]
    chat_margin: tuple[int, int, int, int]
    chat_width_ratio: float
    result_preview_lines: int
    visible_operations: int
    show_metadata: bool
    two_column_status: bool
    vertical_gap: int
    prompt_symbol: str = "❯"

    @classmethod
    def for_width(
        cls,
        width: int | None,
        *,
        chat_width_ratio: float = 0.85,
        chat_padding: tuple[int, int] = (0, 2),
        chat_margin: tuple[int, int, int, int] = (0, 0, 1, 0),
    ) -> LayoutMetrics:
        """Create one stable metric set for a terminal width.

        Theme overrides are accepted only for values belonging to the theme;
        the density breakpoints remain owned by ``decide_cli_visual``.
        """
        normalized_width = width if isinstance(width, int) else _DEFAULT_WIDTH
        normalized_width = max(normalized_width, _MIN_WIDTH)
        plan = decide_cli_visual(normalized_width)
        ratio = min(max(float(chat_width_ratio), 0.45), 1.0)
        return cls(
            width=normalized_width,
            density=plan.density,
            group_padding=plan.group_padding,
            focus_padding=(1, 2),
            chat_padding=chat_padding,
            chat_margin=chat_margin,
            chat_width_ratio=ratio,
            result_preview_lines=plan.result_preview_lines,
            visible_operations=plan.visible_operations,
            show_metadata=plan.show_metadata,
            two_column_status=plan.dashboard_columns,
            vertical_gap=1 if plan.density is not CliDensity.COMPACT else 0,
        )

    @property
    def content_width(self) -> int:
        """Return usable width after the compact outer gutter."""
        return max(1, self.width - 2 * self.group_padding[1])

    @property
    def chat_width(self) -> int:
        """Return the maximum width of a conversation bubble."""
        return max(1, int(self.content_width * self.chat_width_ratio))

    @property
    def narrow(self) -> bool:
        """Return whether the terminal requires compact presentation."""
        return self.density is CliDensity.COMPACT

    def fit_inline(self, value: str, *, reserve: int = _MAX_INLINE_RESERVE) -> str:
        """Keep one-line metadata within the available width."""
        text = str(value).replace("\n", " ").strip()
        limit = max(1, self.width - max(reserve, 0))
        if len(text) <= limit:
            return text
        if limit <= 1:
            return text[:limit]
        return text[: limit - 1].rstrip() + "…"

    def truncate_label(self, value: str, *, minimum: int = 8) -> str:
        """Truncate a context label without producing an empty label."""
        limit = max(minimum, self.width // 3)
        return self.fit_inline(value, reserve=max(self.width - limit, 0))


def layout_for_width(width: int | None, **overrides: object) -> LayoutMetrics:
    """Convenience factory used by renderers and tests."""
    return LayoutMetrics.for_width(width, **overrides)  # type: ignore[arg-type]


__all__ = ["LayoutMetrics", "layout_for_width"]
