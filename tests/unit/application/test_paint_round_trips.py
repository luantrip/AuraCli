"""Round-trip gates for the headless Paint bounded context."""

from rich.style import Style

from aura_cli.application.paint.animation import Animation, Frame, LoopMode
from aura_cli.application.paint.ansi_art_document import AnsiArtDocument
from aura_cli.application.paint.layers import LayerCell, LayerStack
from aura_cli.application.paint.localization import i18n


def _document() -> AnsiArtDocument:
    document = AnsiArtDocument.from_text("AB\nCD")
    document.st[0][0] = Style(color="#ff0000", bgcolor="#0000ff")
    return document


def test_ansi_round_trip_preserves_cells_and_dimensions() -> None:
    original = _document()

    restored = AnsiArtDocument.from_ansi(original.get_ansi())

    assert (restored.width, restored.height) == (original.width, original.height)
    assert restored.ch == original.ch
    assert restored.st[0][0].color.triplet == original.st[0][0].color.triplet
    assert restored.st[0][0].bgcolor.triplet == original.st[0][0].bgcolor.triplet


def test_svg_embedded_ansi_round_trip_preserves_document() -> None:
    original = _document()

    encoded = original.encode_to_format("SVG")
    restored = AnsiArtDocument.decode_based_on_file_extension(encoded, "art.svg")

    assert restored.ch == original.ch
    assert restored.st[0][0].color.triplet == original.st[0][0].color.triplet


def test_raster_export_round_trip_preserves_dimensions_and_background() -> None:
    original = _document()

    restored = AnsiArtDocument.from_image_format(original.encode_to_format("PNG"))

    assert (restored.width, restored.height) == (2, 2)
    assert restored.st[0][0].bgcolor == original.st[0][0].bgcolor


def test_layer_stack_round_trip_preserves_cells_and_active_layer() -> None:
    stack = LayerStack(2, 1)
    foreground = stack.add_layer("Foreground")
    foreground.set_cell(
        0,
        0,
        LayerCell("X", "#ff0000", "#0000ff", is_transparent=False),
    )

    restored = LayerStack.from_dict(stack.to_dict())

    assert restored.active_layer is not None
    assert restored.active_layer.name == "Foreground"
    assert restored.to_document().ch[0][0] == "X"
    assert restored.to_document().st[0][0].color.name == "#ff0000"


def test_animation_round_trip_preserves_frames_and_settings() -> None:
    animation = Animation(2, 2)
    animation.name = "Blink"
    animation.loop_mode = LoopMode.PING_PONG
    animation.current_frame.ch[0][0] = "A"  # type: ignore[union-attr]
    animation.add_frame(Frame.from_document(_document(), name="Second"))

    restored = Animation.from_dict(animation.to_dict())

    assert restored.name == "Blink"
    assert restored.loop_mode is LoopMode.PING_PONG
    assert restored.frame_count == 2
    assert restored.current_frame is not None
    assert restored.current_frame.ch[0][0] == "A"


def test_localization_hotkey_round_trip_and_language_reset() -> None:
    i18n.load_language("en")
    label = "&Open"

    assert i18n.get_hotkey(label) == "O"
    assert i18n.remove_hotkey(label) == "Open"
    assert i18n.markup_hotkey(label) == "[u]O[/u]pen"
    assert i18n.get_direction() == "ltr"
