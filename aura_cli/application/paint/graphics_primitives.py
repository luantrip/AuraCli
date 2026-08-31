"""Graphics Primitives - Aura CLI Paint Tool

Drawing algorithms for AnsiArtDocument.

Features:
    - Bresenham line algorithm
    - Polygon and polyline rendering
    - Bezier and quadratic curves
    - Midpoint ellipse algorithm
    - Flood fill with color matching
    - Point-in-polygon testing
"""

from typing import TYPE_CHECKING, Iterator, List, Tuple

from rich.color import Color
from rich.style import Style
from textual.geometry import Offset, Region

if TYPE_CHECKING:
    from .ansi_art_document import AnsiArtDocument


def bresenham_walk(x0: int, y0: int, x1: int, y1: int) -> Iterator[Tuple[int, int]]:
    """Generate points along line using Bresenham's algorithm.

    Args:
        x0, y0: Start coordinates
        x1, y1: End coordinates

    Yields:
        (x, y) tuples for each point on the line
    """
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        yield x0, y0
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err = err - dy
            x0 = x0 + sx
        if e2 < dx:
            err = err + dx
            y0 = y0 + sy


def polygon_walk(points: List[Offset]) -> Iterator[Tuple[int, int]]:
    """Generate points along polygon perimeter.

    Args:
        points: List of (x, y) vertices

    Yields:
        (x, y) tuples for each point on perimeter
    """
    for i in range(len(points)):
        yield from bresenham_walk(
            points[i][0],
            points[i][1],
            points[(i + 1) % len(points)][0],
            points[(i + 1) % len(points)][1],
        )


def polyline_walk(points: List[Offset]) -> Iterator[Tuple[int, int]]:
    """Generate points along polyline (unclosed polygon).

    Args:
        points: List of (x, y) vertices

    Yields:
        (x, y) tuples for each point on polyline
    """
    for i in range(len(points) - 1):
        yield from bresenham_walk(
            points[i][0], points[i][1], points[i + 1][0], points[i + 1][1]
        )


def is_inside_polygon(x: int, y: int, points: List[Offset]) -> bool:
    """Test if point is inside polygon using ray casting.

    Args:
        x, y: Point coordinates to test
        points: List of (x, y) polygon vertices

    Returns:
        True if point is inside polygon
    """
    n = len(points)
    inside = False
    p1x, p1y = points[0]
    for i in range(n + 1):
        p2x, p2y = points[i % n]
        if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
            x_intersection: float = x
            if p1y != p2y:
                x_intersection = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= x_intersection:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside


# def polygon_fill(points: List[Offset]) -> Iterator[Tuple[int, int]]:
#     """Yields points inside a polygon."""

#     # Find the bounding box
#     min_x = min(points, key=lambda p: p[0])[0]
#     min_y = min(points, key=lambda p: p[1])[1]
#     max_x = max(points, key=lambda p: p[0])[0]
#     max_y = max(points, key=lambda p: p[1])[1]

#     # Check each point in the bounding box, and yield any points that are inside the polygon
#     for x in range(min_x, max_x + 1):
#         for y in range(min_y, max_y + 1):
#             if is_inside_polygon(x, y, points):
#                 yield x, y


def compute_bezier(
    t: float,
    start_x: float,
    start_y: float,
    control_1_x: float,
    control_1_y: float,
    control_2_x: float,
    control_2_y: float,
    end_x: float,
    end_y: float,
) -> Tuple[float, float]:
    """Calculate point on cubic Bezier curve at parameter t.

    Args:
        t: Parameter value (0.0 to 1.0)
        start_x, start_y: Start point coordinates
        control_1_x, control_1_y: First control point
        control_2_x, control_2_y: Second control point
        end_x, end_y: End point coordinates

    Returns:
        (x, y) tuple for point at parameter t
    """
    mt = 1 - t
    mt2 = mt * mt
    t2 = t * t

    a = mt2 * mt
    b = mt2 * t * 3
    c = mt * t2 * 3
    d = t * t2

    return (
        a * start_x + b * control_1_x + c * control_2_x + d * end_x,
        a * start_y + b * control_1_y + c * control_2_y + d * end_y,
    )


def bezier_curve_walk(
    start_x: float,
    start_y: float,
    control_1_x: float,
    control_1_y: float,
    control_2_x: float,
    control_2_y: float,
    end_x: float,
    end_y: float,
) -> Iterator[Tuple[int, int]]:
    """Generate points along cubic Bezier curve.

    Args:
        start_x, start_y: Start point coordinates
        control_1_x, control_1_y: First control point
        control_2_x, control_2_y: Second control point
        end_x, end_y: End point coordinates

    Yields:
        (x, y) tuples for each point on curve
    """
    steps = 100
    point_a = (start_x, start_y)
    for i in range(steps):
        t = i / steps
        point_b = compute_bezier(
            t,
            start_x,
            start_y,
            control_1_x,
            control_1_y,
            control_2_x,
            control_2_y,
            end_x,
            end_y,
        )
        yield from bresenham_walk(
            int(point_a[0]), int(point_a[1]), int(point_b[0]), int(point_b[1])
        )
        point_a = point_b


def quadratic_curve_walk(
    start_x: float,
    start_y: float,
    control_x: float,
    control_y: float,
    end_x: float,
    end_y: float,
) -> Iterator[Tuple[int, int]]:
    """Generate points along quadratic Bezier curve.

    Args:
        start_x, start_y: Start point coordinates
        control_x, control_y: Control point
        end_x, end_y: End point coordinates

    Yields:
        (x, y) tuples for each point on curve
    """
    return bezier_curve_walk(
        start_x, start_y, control_x, control_y, control_x, control_y, end_x, end_y
    )


def midpoint_ellipse(xc: int, yc: int, rx: int, ry: int) -> Iterator[Tuple[int, int]]:
    """Generate ellipse points using midpoint algorithm.

    Args:
        xc, yc: Center coordinates
        rx: Horizontal radius
        ry: Vertical radius

    Yields:
        (x, y) tuples for each point on ellipse (unordered due to 4-way symmetry)
    """

    x = 0
    y = ry

    d1 = (ry * ry) - (rx * rx * ry) + (0.25 * rx * rx)
    dx = 2 * ry * ry * x
    dy = 2 * rx * rx * y

    while dx < dy:
        yield x + xc, y + yc
        yield -x + xc, y + yc
        yield x + xc, -y + yc
        yield -x + xc, -y + yc

        if d1 < 0:
            x += 1
            dx = dx + (2 * ry * ry)
            d1 = d1 + dx + (ry * ry)
        else:
            x += 1
            y -= 1
            dx = dx + (2 * ry * ry)
            dy = dy - (2 * rx * rx)
            d1 = d1 + dx - dy + (ry * ry)

    d2 = (
        ((ry * ry) * ((x + 0.5) * (x + 0.5)))
        + ((rx * rx) * ((y - 1) * (y - 1)))
        - (rx * rx * ry * ry)
    )

    while y >= 0:
        yield x + xc, y + yc
        yield -x + xc, y + yc
        yield x + xc, -y + yc
        yield -x + xc, -y + yc

        if d2 > 0:
            y -= 1
            dy = dy - (2 * rx * rx)
            d2 = d2 + (rx * rx) - dy
        else:
            y -= 1
            x += 1
            dx = dx + (2 * ry * ry)
            dy = dy - (2 * rx * rx)
            d2 = d2 + dx - dy + (rx * rx)


def flood_fill(
    document: "AnsiArtDocument",
    x: int,
    y: int,
    fill_ch: str,
    fill_fg: str,
    fill_bg: str,
) -> Region | None:
    """Fill contiguous region with specified character and colors.

    Args:
        document: AnsiArtDocument to modify
        x, y: Starting coordinates for fill
        fill_ch: Character to fill with
        fill_fg: Foreground color string
        fill_bg: Background color string

    Returns:
        Region affected by fill, or None if starting point doesn't match

    Note:
        Uses span-based flood fill algorithm. Compares colors numerically
        with threshold of 5 to handle color format differences.
    """

    fill_style = Style(color=fill_fg, bgcolor=fill_bg)

    original_style = document.st[y][x]
    original_ch = document.ch[y][x]

    min_x = x
    min_y = y
    max_x = x
    max_y = y

    def colors_match(a: Color, b: Color) -> bool:
        """Compare colors numerically with threshold.

        Args:
            a, b: Colors to compare

        Returns:
            True if colors match within threshold of 5
        """
        threshold = 5
        assert a.triplet is not None
        assert b.triplet is not None
        return all(abs(a.triplet[i] - b.triplet[i]) < threshold for i in range(3))

    def inside(x: int, y: int) -> bool:
        """Check if cell matches original color and differs from fill.

        Args:
            x, y: Cell coordinates to check

        Returns:
            True if cell should be filled

        Note:
            Ignores foreground color if character is space (transparent).
        """
        if x < 0 or x >= document.width or y < 0 or y >= document.height:
            return False

        bgcolor = document.st[y][x].bgcolor
        color = document.st[y][x].color
        assert bgcolor is not None
        assert color is not None
        assert original_style.bgcolor is not None
        assert original_style.color is not None
        assert fill_style.color is not None
        assert fill_style.bgcolor is not None
        return (
            document.ch[y][x] == original_ch
            and colors_match(bgcolor, original_style.bgcolor)
            and (original_ch == " " or colors_match(color, original_style.color))
            and (
                document.ch[y][x] != fill_ch
                or (not colors_match(bgcolor, fill_style.bgcolor))
                or (not colors_match(color, fill_style.color))
            )
        )

    def set_cell(x: int, y: int) -> None:
        """Set cell to fill color and update region bounds.

        Args:
            x, y: Cell coordinates to fill
        """
        document.ch[y][x] = fill_ch
        document.st[y][x] = fill_style
        nonlocal min_x, min_y, max_x, max_y
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)

    if not inside(x, y):
        return None
    stack: List[Tuple[int, int, int, int]] = [(x, x, y, 1), (x, x, y - 1, -1)]
    while stack:
        x1, x2, y, dy = stack.pop()
        x = x1
        if inside(x, y):
            while inside(x - 1, y):
                set_cell(x - 1, y)
                x = x - 1
        if x < x1:
            stack.append((x, x1 - 1, y - dy, -dy))
        while x1 <= x2:
            while inside(x1, y):
                set_cell(x1, y)
                x1 = x1 + 1
                stack.append((x, x1 - 1, y + dy, dy))
                if x1 - 1 > x2:
                    stack.append((x2 + 1, x1 - 1, y - dy, -dy))
            x1 = x1 + 1
            while x1 < x2 and not inside(x1, y):
                x1 = x1 + 1
            x = x1

    return Region(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
