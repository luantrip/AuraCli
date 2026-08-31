"""Print utilities for Paint Tool.

Provides print preview, page setup, and printing functionality.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aura_cli.tui.tools.paint.paint import Paint

from aura_cli.application.paint.localization.i18n import get as _


def show_print_preview(paint_instance: "Paint") -> None:
    """Show print preview dialog.

    Args:
        paint_instance: The Paint instance
    """
    paint_instance.message_box(
        _("Print Preview"),
        _(
            "Print preview shows how the image will appear when printed.\n\n"
            "This feature requires system print capabilities.\n"
            "For now, you can export the image and print it using your system's print dialog."
        ),
        "ok",
    )


def show_page_setup(paint_instance: "Paint") -> None:
    """Show page setup dialog.

    Args:
        paint_instance: The Paint instance
    """
    paint_instance.message_box(
        _("Page Setup"),
        _(
            "Page setup allows configuring:\n"
            "- Page size (A4, Letter, etc.)\n"
            "- Orientation (Portrait/Landscape)\n"
            "- Margins\n\n"
            "This feature requires system print capabilities.\n"
            "For now, you can export the image and configure printing using your system's print dialog."
        ),
        "ok",
    )


def print_image(paint_instance: "Paint") -> None:
    """Print the current image.

    Args:
        paint_instance: The Paint instance
    """
    paint_instance.message_box(
        _("Print"),
        _(
            "Printing sends the image to a printer.\n\n"
            "This feature requires system print capabilities.\n"
            "For now, you can export the image (File > Export) and print it using your system's print dialog."
        ),
        "ok",
    )
