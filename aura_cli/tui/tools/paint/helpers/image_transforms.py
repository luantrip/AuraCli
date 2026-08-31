"""Compatibility facade for Application-owned Paint transformations."""

from aura_cli.application.paint.transformations import (
    flip_horizontal as flip_image_horizontal,
)
from aura_cli.application.paint.transformations import (
    flip_vertical as flip_image_vertical,
)
from aura_cli.application.paint.transformations import rotate as rotate_image_by_angle

__all__ = [
    "flip_image_horizontal",
    "flip_image_vertical",
    "rotate_image_by_angle",
]
