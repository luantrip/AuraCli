"""Paint Tool Integration Module - Aura CLI.

Provides integration functions for connecting animation and widget systems
to the main Paint application without tight coupling.

This module serves as a clean API boundary between the Paint app and
the new animation/widget features, enabling modular integration.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .paint import Paint

from aura_cli.application.paint.animation import AnimationFrame, AnimationTimeline
from aura_cli.application.paint.onion_skin import OnionSkinRenderer, OnionSkinSettings

from .animation_export import AnimationExporter


def init_animation_system(app: "Paint") -> None:
    """Initialize animation system for paint application.

    Sets up timeline, onion skinning, and creates initial frame
    with current layer stack.

    Args:
        app: Paint application instance
    """
    app.animation_timeline = AnimationTimeline()
    app.onion_skin_settings = OnionSkinSettings()
    app.onion_skin_renderer = OnionSkinRenderer(app.onion_skin_settings)

    initial_frame = AnimationFrame()
    initial_frame.layer_stack = app.layer_stack
    app.animation_timeline.add_frame(initial_frame)


def handle_opacity_changed(app: "Paint", opacity: float) -> None:
    """Handle opacity slider value changes.

    Updates active layer opacity and refreshes canvas.

    Args:
        app: Paint application instance
        opacity: Normalized opacity value (0.0-1.0)
    """
    if app.layer_stack and app.layer_stack.active_layer:
        layer = app.layer_stack.active_layer
        layer.opacity = opacity
        app.canvas.refresh()


def handle_blend_mode_changed(app: "Paint", blend_mode) -> None:
    """Handle blend mode selector changes.

    Updates active layer blend mode and refreshes canvas.

    Args:
        app: Paint application instance
        blend_mode: Selected blend mode enum value
    """
    if app.layer_stack and app.layer_stack.active_layer:
        layer = app.layer_stack.active_layer
        layer.blend_mode = blend_mode
        app.canvas.refresh()


def handle_layer_renamed(app: "Paint", layer_id: str, new_name: str) -> None:
    """Handle layer rename operations.

    Updates layer name in layer stack.

    Args:
        app: Paint application instance
        layer_id: Unique identifier of layer to rename
        new_name: New name for the layer
    """
    layer = app.layer_stack.get_layer(layer_id)
    if layer:
        layer.name = new_name


def handle_frame_changed(app: "Paint", frame_index: int) -> None:
    """Handle timeline frame selection changes.

    Loads selected frame's layer stack into application and refreshes canvas.

    Args:
        app: Paint application instance
        frame_index: Index of frame to activate
    """
    active_frame = app.animation_timeline.active_frame
    if active_frame and active_frame.layer_stack:
        app.layer_stack = active_frame.layer_stack
        app.canvas.refresh()


def handle_export_animation(app: "Paint", format_type: str, filename: str) -> bool:
    """Handle animation export requests.

    Exports animation timeline to specified format and filename.

    Args:
        app: Paint application instance
        format_type: Export format (gif/sprite/ansi)
        filename: Target filename for export

    Returns:
        True if export succeeded, False otherwise
    """
    exporter = AnimationExporter()

    format_handlers = {
        "gif": exporter.export_gif,
        "sprite": exporter.export_sprite_sheet,
        "ansi": exporter.export_ansi_sequence,
    }

    handler = format_handlers.get(format_type)
    if handler:
        return handler(app.animation_timeline, filename)

    return False


def sync_app_to_frame(app: "Paint") -> None:
    """Synchronize application state to active frame.

    Copies current layer stack to active frame for persistence.

    Args:
        app: Paint application instance
    """
    active_frame = app.animation_timeline.active_frame
    if active_frame:
        active_frame.layer_stack = app.layer_stack


def sync_frame_to_app(app: "Paint") -> None:
    """Synchronize active frame to application state.

    Loads active frame's layer stack into application and refreshes canvas.

    Args:
        app: Paint application instance
    """
    active_frame = app.animation_timeline.active_frame
    if active_frame and active_frame.layer_stack:
        app.layer_stack = active_frame.layer_stack
        app.canvas.refresh()
