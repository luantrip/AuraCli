"""Undo/redo helper functions for Paint tool."""

from typing import Optional

from textual.geometry import Region

from aura_cli.application.paint.action import Action
from aura_cli.application.paint.ansi_art_document import AnsiArtDocument


def _create_undo_state(
    image,
    add_action_func,
    action_name: str,
    region: Optional[Region] = None,
    is_full_update: bool = False,
) -> tuple[AnsiArtDocument, Action]:
    """Create an undo state helper.

    Args:
        image: Current image document
        add_action_func: Function to add action to undo stack
        action_name: Name of the action
        region: Affected region (optional)
        is_full_update: If True, captures full document state

    Returns:
        Tuple of (image_at_start, action)
    """
    image_at_start = AnsiArtDocument(image.width, image.height)
    image_at_start.copy_region(image)
    action = Action(action_name)
    add_action_func(action)
    if region:
        action.region = region.intersection(Region(0, 0, image.width, image.height))
    elif is_full_update:
        action.region = Region(0, 0, image.width, image.height)
        action.is_full_update = True
    return image_at_start, action
