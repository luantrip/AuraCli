"""Rasterize ANSI Art - Aura CLI Paint Tool

Convert ANSI art documents to PIL images for wallpaper export.

Features:
    - Multi-platform font discovery (Windows, macOS, Linux, Android)
    - Prioritized font list with Unicode coverage (Noto Sans Mono first)
    - Fallback to built-in font if no system fonts found
    - Cell-by-cell rendering with background and foreground colors
    - Unicode character support with error handling
"""

import contextlib
import os
from pathlib import Path
from typing import TYPE_CHECKING

from PIL import Image, ImageDraw, ImageFont

if TYPE_CHECKING:
    from aura_cli.application.paint.ansi_art_document import AnsiArtDocument

font_dirs = [
    R"C:\Windows\Fonts",
    R"C:\WINNT\Fonts",
    R"%LocalAppData%\Microsoft\Windows\Fonts",
    "/Library/Fonts",
    "/System/Library/Fonts",
    "~/Library/Fonts",
    *[
        data_dir + "/fonts"
        for data_dir in os.environ.get("XDG_DATA_DIRS", "/usr/share").split(":")
    ],
    "/usr/local/share/fonts",
    "~/.fonts",
    "/system/fonts",
    "/data/fonts",
]
font_names = [
    "Noto Sans Mono",
    "Cascadia Mono",
    "Cascadia Code",
    "DejaVu Sans Mono",
    "Liberation Mono",
    "Ubuntu Mono",
    "Hack",
    "Fira Mono",
    "Inconsolata",
    "Source Code Pro",
    "Droid Sans Mono",
    "Consolas",
    "Consola",
    "Courier New",
    "Lucida Console",
    "Monaco",
    "Menlo",
    "Andale Mono",
    "Cour",
]


def normalize_font_name(name: str) -> str:
    """Normalize font name for comparison.

    Args:
        name: Font name to normalize

    Returns:
        Lowercase name with spaces, dashes, and underscores removed
    """
    return name.lower().replace(" ", "").replace("-", "").replace("_", "")


font_names = [normalize_font_name(name) for name in font_names]

font = None
for font_dir in font_dirs:
    path = Path(os.path.expandvars(os.path.expanduser(font_dir)))
    files = path.glob("**/*.ttf")
    files = list(files)
    for file in files:
        if normalize_font_name(file.stem) in font_names:
            font = ImageFont.truetype(
                str(file), size=16, layout_engine=ImageFont.Layout.BASIC
            )
            break
    if font:
        break
if not font:
    print(
        "Font not found, falling back to built-in font for ANSI art rasterization if Set As Wallpaper feature is used."
    )
    font = ImageFont.load_default()

# Calculate character size
if hasattr(font, "getbbox"):
    left, top, right, bottom = font.getbbox("A")
    ch_width = int(right - left)
    ch_height = int(bottom - top)
    # Some fonts might return 0 or small values, ensure defaults
    if ch_width <= 0:
        ch_width = 8
    if ch_height <= 0:
        ch_height = 16
else:
    # Older Pillow versions
    ch_width, ch_height = font.getsize("A")  # type: ignore

assert isinstance(ch_width, int)
assert isinstance(ch_height, int)


def rasterize(doc: "AnsiArtDocument") -> Image.Image:
    """Render ANSI art document as PIL image.

    Args:
        doc: AnsiArtDocument to rasterize

    Returns:
        PIL Image with rendered ANSI art

    Note:
        Renders cell backgrounds first, then text. Handles Unicode
        encoding errors gracefully by skipping problematic characters.
    """
    img = Image.new(
        "RGB", (doc.width * ch_width, doc.height * ch_height), color="black"
    )
    draw = ImageDraw.Draw(img)

    for y in range(doc.height):
        for x in range(doc.width):
            bg_color = doc.st[y][x].bgcolor
            assert bg_color is not None
            draw.rectangle(
                (x * ch_width, y * ch_height, (x + 1) * ch_width, (y + 1) * ch_height),
                fill=bg_color.get_truecolor().hex,
            )

    for y in range(doc.height):
        for x in range(doc.width):
            char = doc.ch[y][x]
            fg_color = doc.st[y][x].color
            assert fg_color is not None
            with contextlib.suppress(UnicodeEncodeError):
                draw.text(
                    (x * ch_width, y * ch_height),
                    char,
                    font=font,
                    fill=fg_color.get_truecolor().hex,
                )

    return img
