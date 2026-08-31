"""Compatibility helpers backed by the Application Paint drawing controller."""

from textual.geometry import Offset, Region

from aura_cli.application.paint.drawing import DrawShape, apply_points, shape_points


def _draw(shape, stamp_brush_func, start, end, affected_region=None) -> Region:
    return apply_points(
        shape_points(shape, start, end), stamp_brush_func, affected_region
    )


def _draw_point_tool(
    stamp_brush_func, start: Offset, end: Offset, affected_region=None
):
    return _draw(DrawShape.LINE, stamp_brush_func, start, end, affected_region)


_draw_line_tool = _draw_point_tool


def _draw_rectangle_tool(stamp_brush_func, start, end, affected_region=None):
    return _draw(DrawShape.RECTANGLE, stamp_brush_func, start, end, affected_region)


def _draw_rounded_rectangle_tool(stamp_brush_func, start, end, affected_region=None):
    return _draw(
        DrawShape.ROUNDED_RECTANGLE,
        stamp_brush_func,
        start,
        end,
        affected_region,
    )


def _draw_ellipse_tool(stamp_brush_func, start, end, affected_region=None):
    return _draw(DrawShape.ELLIPSE, stamp_brush_func, start, end, affected_region)


__all__ = [
    "_draw_ellipse_tool",
    "_draw_line_tool",
    "_draw_point_tool",
    "_draw_rectangle_tool",
    "_draw_rounded_rectangle_tool",
]
