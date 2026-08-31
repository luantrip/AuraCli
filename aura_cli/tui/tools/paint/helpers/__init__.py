"""Helper functions for Paint tool.

This module provides helper functions that can be used as mixins or utilities
for the Paint class. The functions are designed to work with the Paint instance
methods through function passing.
"""

from .drawing_helpers import (
    _draw_ellipse_tool,
    _draw_line_tool,
    _draw_point_tool,
    _draw_rectangle_tool,
    _draw_rounded_rectangle_tool,
)
from .error_handlers import (
    _get_full_region,
    _handle_file_error,
    _handle_operation_error,
    _handle_validation_error,
)
from .image_transforms import (
    flip_image_horizontal,
    flip_image_vertical,
    rotate_image_by_angle,
)
from .undo_helpers import _create_undo_state

__all__ = [
    "_create_undo_state",
    "_draw_ellipse_tool",
    "_draw_line_tool",
    "_draw_point_tool",
    "_draw_rectangle_tool",
    "_draw_rounded_rectangle_tool",
    "_get_full_region",
    "_handle_file_error",
    "_handle_operation_error",
    "_handle_validation_error",
    "flip_image_horizontal",
    "flip_image_vertical",
    "rotate_image_by_angle",
]
