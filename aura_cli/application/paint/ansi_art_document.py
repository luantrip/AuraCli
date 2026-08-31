"""ANSI Art Document - Aura CLI Paint Tool

Core document model for ANSI art with selection and format support.

Features:
    - 2D character and style grids
    - Selection with textbox and cursor modes
    - ANSI escape sequence parsing and generation
    - Multiple format support (ANSI, SVG, HTML, PNG, etc.)
    - Undo/redo with region updates
    - Image loading from various formats
    - Flexible character grid for SVG loading
    - IRC palette support
"""

import base64
import io
import math
import os
from random import randint
import re
from typing import (
    Any,
    Dict,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
)

import defusedxml.ElementTree as ET
from PIL import Image
from rich.color import Color as RichColor
from rich.console import Console
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
import stransi
from textual.color import Color, ColorParseError
from textual.geometry import Offset, Region

from .export_templates import CUSTOM_CONSOLE_HTML_FORMAT, CUSTOM_CONSOLE_SVG_FORMAT
from .localization.i18n import get as _
from .palette_data import IRC_PALETTE

DEBUG_REGION_UPDATES = False

DEBUG_SVG_LOADING = (
    False  # writes debug.svg when flexible character grid loader is used
)

# JPEG is disabled because of low quality.
# On the scale of images you're able to (performantly) edit in this app (currently),
# JPEG is not a good choice.
# ICNS is disabled because it only supports a limited set of sizes.
SAVE_DISABLED_FORMATS = ["JPEG", "ICNS"]


# Detects ANSI escape sequences.
# ansi_escape_pattern = re.compile(r"(\N{ESC}\[[\d;]*[a-zA-Z])")

# Detects all control codes, including newlines and tabs.
# ansi_control_code_pattern = re.compile(r'[\x00-\x1F\x7F]')

# Detects all control codes, including tabs and carriage return (CR) if used alone, but excluding line feed (LF) and CR+LF.
ansi_detector_pattern = re.compile(r"[\x00-\x09\x0B\x0C\x0E-\x1F\x7F]|\r(?!\n)")
# Explanation:
# [\x00-\x09\x0B\x0C\x0E-\x1F\x7F]: Matches any control character except CR (\x0D) or LF (\x0A).
# \r(?<!\r\n): Matches CR (\x0D) if it's not part of CRLF (\x0D\x0A).
#   (?<!\r\n): Negative lookbehind assertion to ensure that the matched CR (if any) is not part of CRLF.
# Tabs are included because they need to be expanded to spaces or they'll mess up the layout, currently,
# and if the text isn't detected as ANSI, it won't currently be expanded.
# Development strategy:
# I used https://www.debuggex.com/ to develop a simpler regex that operates on letters as stand-ins for control codes,
# since I don't know that I could input isolated control codes into the site.
# e|r(?!n)
# using test data:
# ---e--- (e representing any control code except CR or LF)
# ---r---
# ---n--- <- shouldn't match
# ---rn-- <- shouldn't match
# ---nr--

assert ansi_detector_pattern.search("\x0a") is None, (
    "LF should not be matched by ansi_detector_pattern"
)
assert ansi_detector_pattern.search("\x0d") is not None, (
    "CR by itself (not part of CRLF) should be matched by ansi_detector_pattern"
)
assert ansi_detector_pattern.search("\x0d\x0a") is None, (
    "CRLF should not be matched by ansi_detector_pattern"
)
assert ansi_detector_pattern.search("\x09") is not None, (
    "TAB should be matched by ansi_detector_pattern"
)
assert ansi_detector_pattern.search("\x1b") is not None, (
    "ESC should be matched by ansi_detector_pattern"
)
assert ansi_detector_pattern.search("\x7f") is not None, (
    "DEL should be matched by ansi_detector_pattern"
)
assert ansi_detector_pattern.search("\x00") is not None, (
    "NUL should be matched by ansi_detector_pattern"
)
assert ansi_detector_pattern.search("\x80") is None, (
    "Ç (in CP 437) or € (U+0080) should not be matched by ansi_detector_pattern"
)


class FormatWriteNotSupported(Exception):
    """The format doesn't support writing."""

    def __init__(self, localized_message: str):
        self.localized_message = localized_message
        super().__init__(localized_message)


class FormatReadNotSupported(Exception):
    """The format doesn't support reading."""

    def __init__(self, localized_message: str):
        self.localized_message = localized_message
        super().__init__(localized_message)


class AnsiArtDocument:
    """A document that can be rendered as ANSI."""

    def __init__(
        self,
        width: int,
        height: int,
        default_bg: str = "#ffffff",
        default_fg: str = "#000000",
    ) -> None:
        """Initialize the document."""
        # Pyright is really confused by height for some reason, doesn't have a problem with width.
        # I narrowed it down to the resize method, lines with new_bg/new_fg, but
        # I have no idea why that would be a problem.
        # Ideally I would try to pare this down to a minimal reproducible example,
        # and file a bug report (or learn something about my code),
        # but for now, I just want to silence 100+ errors.
        # I'm leaving width unannotated to highlight the fragility of programming.
        self.width = width
        self.height: int = height
        self.ch = [[" " for _ in range(width)] for _ in range(height)]
        """2D array of characters."""
        style = Style(color=default_fg, bgcolor=default_bg)
        self.st = [[style for _ in range(width)] for _ in range(height)]
        """2D array of styles."""
        self.selection: Optional[Selection] = None
        """The current selection, which can itself contain an ANSI art document."""

    def copy(self, source: "AnsiArtDocument") -> None:
        """Copy the image size and data from another document. Does not copy the selection."""
        self.width = source.width
        self.height = source.height
        self.ch = [row[:] for row in source.ch]
        self.st = [row[:] for row in source.st]
        self.selection = None

    def copy_region(
        self,
        source: "AnsiArtDocument",
        source_region: Region | None = None,
        target_region: Region | None = None,
        mask: List[List[bool]] | None = None,
        transparent: bool = False,
    ) -> None:
        """Copy a region from another document into this document.

        Args:
            source: Source document to copy from
            source_region: Region in source document to copy
            target_region: Region in this document to copy to
            mask: Optional mask for selective copying
            transparent: If True, skip spaces (transparent mode)
        """
        if source_region is None:
            source_region = Region(0, 0, source.width, source.height)
        if target_region is None:
            target_region = Region(0, 0, source_region.width, source_region.height)
        source_offset = source_region.offset
        target_offset = target_region.offset
        random_color: Optional[str] = None
        if DEBUG_REGION_UPDATES:
            random_color = (
                "rgb("
                + str(randint(0, 255))
                + ","
                + str(randint(0, 255))
                + ","
                + str(randint(0, 255))
                + ")"
            )
        for y in range(target_region.height):
            for x in range(target_region.width):
                if source_region.contains(
                    x + source_offset.x, y + source_offset.y
                ) and (mask is None or mask[y][x]):
                    source_char = source.ch[y + source_offset.y][x + source_offset.x]
                    if transparent and source_char == " ":
                        continue
                    self.ch[y + target_offset.y][x + target_offset.x] = source_char
                    self.st[y + target_offset.y][x + target_offset.x] = source.st[
                        y + source_offset.y
                    ][x + source_offset.x]
                    if DEBUG_REGION_UPDATES:
                        assert random_color is not None
                        self.st[y + target_offset.y][x + target_offset.x] += Style(
                            bgcolor=random_color
                        )
                else:
                    if DEBUG_REGION_UPDATES:
                        self.ch[y + target_offset.y][x + target_offset.x] = "?"
                        self.st[y + target_offset.y][x + target_offset.x] = Style(
                            color="#000000", bgcolor="#ff00ff"
                        )

    def resize(
        self,
        width: int,
        height: int,
        default_bg: str = "#ffffff",
        default_fg: str = "#000000",
    ) -> None:
        """Resize the document."""
        if width == self.width and height == self.height:
            return
        new_ch = [[" " for _ in range(width)] for _ in range(height)]
        new_st = [
            [Style(color=default_fg, bgcolor=default_bg) for _ in range(width)]
            for _ in range(height)
        ]
        for y in range(min(height, self.height)):
            for x in range(min(width, self.width)):
                new_ch[y][x] = self.ch[y][x]
                new_st[y][x] = self.st[y][x]
        self.width = width
        self.height = height
        self.ch = new_ch
        self.st = new_st

    @staticmethod
    def _invert_color(color: RichColor) -> RichColor:
        """Return the bitwise-inverted version of a RichColor."""
        assert color.triplet is not None
        t = color.triplet
        return RichColor.parse(
            f"#{(255 - t.red):02x}{(255 - t.green):02x}{(255 - t.blue):02x}"
        )

    def invert(self) -> None:
        """Invert the foreground and background colors."""
        self.invert_region(Region(0, 0, self.width, self.height))

    def clear(self, default_bg: str = "#ffffff", default_fg: str = "#000000") -> None:
        """Reset every cell while preserving document dimensions."""
        default_style = Style(color=default_fg, bgcolor=default_bg)
        for y in range(self.height):
            for x in range(self.width):
                self.ch[y][x] = " "
                self.st[y][x] = default_style

    def invert_region(self, region: Region) -> None:
        """Invert the foreground and background colors in the given region."""
        for y in range(region.y, region.y + region.height):
            for x in range(region.x, region.x + region.width):
                style = self.st[y][x]
                assert style.color is not None
                assert style.bgcolor is not None
                self.st[y][x] = Style.from_color(
                    color=self._invert_color(style.color),
                    bgcolor=self._invert_color(style.bgcolor),
                )

    @staticmethod
    def format_from_extension(file_path: str) -> str | None:
        """Get the format ID from the file extension of the given path.

        Most format IDs are similar to the extension, e.g. 'PNG' for '.png',
        but some are different, e.g. 'JPEG2000' for '.jp2'.
        """
        # Ignore case and trailing '~' (indicating a backup file)
        # Alternative: pathlib.Path.suffix
        file_ext_with_dot = os.path.splitext(file_path)[1].lower().rstrip("~")
        ext_to_id = (
            Image.registered_extensions()
        )  # maps extension to format ID, e.g. '.jp2': 'JPEG2000'
        if file_ext_with_dot in ext_to_id:
            return ext_to_id[file_ext_with_dot]
        ext_to_id = {
            ".svg": "SVG",
            ".html": "HTML",
            ".htm": "HTML",
            ".txt": "PLAINTEXT",
            ".asc": "PLAINTEXT",
            ".diz": "PLAINTEXT",
            ".ans": "ANSI",
            ".irc": "IRC",
            ".mirc": "IRC",
            "._rich_console_markup": "RICH_CONSOLE_MARKUP",
        }
        if file_ext_with_dot in ext_to_id:
            return ext_to_id[file_ext_with_dot]
        return None

    def encode_based_on_file_extension(self, file_path: str) -> bytes:
        """Encode the image according to the file extension."""
        return self.encode_to_format(self.format_from_extension(file_path))

    def encode_to_format(self, format_id: str | None) -> bytes:
        """Encode the image into the given file format."""
        if format_id is None:
            raise FormatWriteNotSupported(
                localized_message=_("Unknown file extension.")
                + "\n\n"
                + _("To save your changes, use a different filename.")
            )
        elif format_id == "ANSI":
            # This maybe shouldn't use UTF-8... but there's not a singular encoding for "ANSI art".
            return self.get_ansi().encode("utf-8")
        elif format_id == "IRC":
            # Also not sure about UTF-8 here.
            return self.get_irc().encode("utf-8")
        elif format_id == "SVG":
            return self.get_svg().encode("utf-8")
        elif format_id == "HTML":
            return self.get_html().encode("utf-8")
        elif format_id == "PLAINTEXT":
            return self.get_plain().encode("utf-8")
        elif format_id == "RICH_CONSOLE_MARKUP":
            return self.get_rich_console_markup().encode("utf-8")
        else:
            # Ensure PIL image formats are initialized
            Image.init()
            if format_id in Image.SAVE and format_id not in SAVE_DISABLED_FORMATS:
                return self.encode_image_format(format_id)
            else:
                raise FormatWriteNotSupported(
                    localized_message=_("Cannot write files in %1 format.", format_id)
                    + "\n\n"
                    + _("To save your changes, use a different filename.")
                )

    def encode_image_format(self, pil_format_id: str) -> bytes:
        """Encode the document as an image file."""
        size = (self.width, self.height)
        image = Image.new("RGB", size, color="#000000")
        pixels = image.load()
        assert pixels is not None, "failed to load pixels for new image"
        for y in range(self.height):
            for x in range(self.width):
                color = self.st[y][x].bgcolor
                assert color is not None
                triplet = color.triplet
                assert triplet is not None
                pixels[x, y] = tuple(triplet)
        buffer = io.BytesIO()
        # `lossless` is for WebP
        # `sizes` is for ICO, since it defaults to a list of square sizes, blurring/distorting the image.
        # `bitmap_format` is also for ICO. I get "Compressed icons are not supported" in Ubuntu's image viewer,
        # and thumbnails don't render when it uses the default PNG sub-format.
        image.save(
            buffer, pil_format_id, lossless=True, sizes=[size], bitmap_format="bmp"
        )
        return buffer.getvalue()

    def get_ansi(self) -> str:
        """Get the ANSI representation of the document."""
        renderable = self.get_renderable()
        console = self.get_console(render_contents=False)
        segments = renderable.render(console=console)
        ansi = ""
        for text, style, _ctrl in Segment.filter_control(Segment.simplify(segments)):
            if style:
                ansi += style.render(text)
            else:
                ansi += text
        return ansi

    def get_irc(self) -> str:
        """Get the mIRC code representation of the document."""
        renderable = self.get_renderable()
        console = self.get_console(render_contents=False)
        segments = renderable.render(console=console)

        def color_distance(a: Color, b: Color) -> float:
            """Perceptual color distance between two colors."""
            # https://www.compuphase.com/cmetric.htm
            red_mean = (a.r + b.r) // 2
            red = a.r - b.r
            green = a.g - b.g
            blue = a.b - b.b
            return math.sqrt(
                (((512 + red_mean) * red * red) >> 8)
                + 4 * green * green
                + (((767 - red_mean) * blue * blue) >> 8)
            )

        def closest_color(color: Color) -> int:
            """Get the closest color in the palette to the given color."""
            closest_color = 0
            closest_distance = float("inf")
            for index, hex_color in enumerate(IRC_PALETTE):
                distance = color_distance(color, Color.parse(hex_color))
                if distance < closest_distance:
                    closest_color = index
                    closest_distance = distance
            return closest_color

        irc_text = ""
        prev_fg: int | None = None
        prev_bg: int | None = None
        for text, style, _ctrl in Segment.filter_control(Segment.simplify(segments)):
            if style and style.color is not None and style.bgcolor is not None:
                fg = closest_color(Color.from_rich_color(style.color))
                bg = closest_color(Color.from_rich_color(style.bgcolor))
                if fg != prev_fg or bg != prev_bg:
                    irc_text += f"\x03{fg},{bg}"
                    if text[0] in "0123456789,":
                        irc_text += "\x03"
                    prev_fg, prev_bg = fg, bg
                irc_text += text
            else:
                irc_text += text
                prev_fg = prev_bg = None
        # ^O is the mIRC code for "reset to default colors"
        return irc_text + "\x0f"

    def get_plain(self) -> str:
        """Get the plain text representation of the document."""
        text = ""
        for y in range(self.height):
            for x in range(self.width):
                text += self.ch[y][x]
            text += os.linesep
        return text

    def get_rich_console_markup(self) -> str:
        """Get the Rich API markup representation of the document."""
        return self.get_renderable().markup

    def get_html(self) -> str:
        """Get the HTML representation of the document."""
        console = self.get_console()
        return console.export_html(
            inline_styles=True, code_format=CUSTOM_CONSOLE_HTML_FORMAT
        )

    def get_svg(self) -> str:
        """Get the SVG representation of the document."""
        console = self.get_console()
        svg = console.export_svg(code_format=CUSTOM_CONSOLE_SVG_FORMAT)
        # Include ANSI in the SVG so it can be loaded perfectly when re-opened.
        # This can't use the .format() template since e.g. "{anything}" in the document would case a KeyError.
        # (And I can't do it beforehand on the template because the template uses .format() itself...
        # unless I escaped all the braces, but that would be ugly! So I'm just using a different syntax.)
        # `html.escape` leaves control codes, which blows up ET.fromstring, so use base64 instead.
        return svg.replace(
            "%ANSI_GOES_HERE%",
            base64.b64encode(self.get_ansi().encode("utf-8")).decode("utf-8"),
        )

    def get_renderable(self) -> Text:
        """Get a Rich renderable for the document."""
        joiner = Text("\n")
        lines: List[Text] = []
        for y in range(self.height):
            line = Text()
            for x in range(self.width):
                line.append(self.ch[y][x], style=self.st[y][x])
            lines.append(line)
        result = joiner.join(lines)
        return result

    def get_console(self, render_contents: bool = True) -> Console:
        """Get a Rich Console with the document rendered in it."""
        console = Console(
            width=self.width,
            height=self.height,
            file=io.StringIO(),
            force_terminal=True,
            color_system="truecolor",
            record=True,
            legacy_windows=False,
        )
        if render_contents:
            console.print(self.get_renderable())
        return console

    @staticmethod
    def from_plain(
        text: str, default_bg: str = "#ffffff", default_fg: str = "#000000"
    ) -> "AnsiArtDocument":
        """Creates a document from the given plain text."""
        lines = text.splitlines()
        width = 1
        for line in lines:
            width = max(len(line), width)
        height = max(len(lines), 1)
        document = AnsiArtDocument(width, height, default_bg, default_fg)
        for y, line in enumerate(lines):
            for x, char in enumerate(line):
                document.ch[y][x] = char
        return document

    @staticmethod
    def from_irc(
        text: str, default_bg: str = "#ffffff", default_fg: str = "#000000"
    ) -> "AnsiArtDocument":
        """Creates a document from text with mIRC codes."""

        default_style = Style(color=default_fg, bgcolor=default_bg)
        document = AnsiArtDocument(0, 0, default_bg, default_fg)
        # Minimum size of 1x1, so that the document is never empty.
        width = 1
        height = 1

        x = 0
        y = 0
        current_style = default_style

        color_escape = "\x03"
        # an optional escape code at the end disambiguates a digit from part of the color code
        color_escape_re = re.compile(r"\x03(\d{1,2})?(?:,(\d{1,2}))?\x03?")
        reset_escape = "\x0f"

        index = 0
        while index < len(text):
            char = text[index]
            if char == color_escape:
                match = color_escape_re.match(text[index:])
                if match:
                    index += len(match.group(0))
                    # A one-value syntax (no background specified) resets the background
                    # to the default, preserving mIRC-compatible behavior.
                    color_change = default_style
                    if match.group(1):
                        color_change += Style.from_color(
                            color=RichColor.parse(IRC_PALETTE[int(match.group(1))])
                        )
                    if match.group(2):
                        color_change += Style.from_color(
                            bgcolor=RichColor.parse(IRC_PALETTE[int(match.group(2))])
                        )
                    current_style += color_change
                    continue
            if char == reset_escape:
                index += 1
                current_style = default_style
                continue
            if char == "\n":
                width = max(width, x)
                x = 0
                y += 1
                height = max(height, y)
                index += 1
                continue
            while len(document.ch) <= y:
                document.ch.append([])
                document.st.append([])
            while len(document.ch[y]) <= x:
                document.ch[y].append(" ")
                document.st[y].append(default_style)
            document.ch[y][x] = char
            document.st[y][x] = current_style
            width = max(x + 1, width)
            height = max(y + 1, height)
            x += 1
            index += 1

        document.width = width
        document.height = height
        del document.ch[document.height :]
        del document.st[document.height :]
        while len(document.ch) < document.height:
            document.ch.append([])
            document.st.append([])
        for y in range(document.height):
            for _unused in range(len(document.ch[y]), document.width):
                document.ch[y].append(" ")
                document.st[y].append(default_style)

        return document

    @staticmethod
    def _ansi_handle_char(
        char: str,
        document: "AnsiArtDocument",
        x: int,
        y: int,
        width: int,
        height: int,
        current_style: Style,
        default_style: Style,
        max_width: int,
    ) -> "Tuple[int, int, int, int]":
        """Process a single character from an ANSI stream. Returns (x, y, width, height)."""
        if char == "\r":
            x = 0
        elif char == "\n":
            x = 0
            y += 1
        elif char == "\t":
            x += 8 - (x % 8)
            if x > max_width - 1:
                x = max_width - 1
        elif char == "\b":
            x = max(0, x - 1)
        elif (
            char
            in "\x07\x00\x01\x02\x03\x04\x05\x06\x08\x0e\x0f\x10\x11\x12\x13\x14\x15\x16\x17\x18\x19\x1a\x1c\x1e\x1f"
        ):
            pass  # ignore bell and other non-printable control characters
        else:
            while len(document.ch) <= y:
                document.ch.append([])
                document.st.append([])
            while len(document.ch[y]) <= x:
                document.ch[y].append(" ")
                document.st[y].append(default_style)
            document.ch[y][x] = char
            document.st[y][x] = current_style
            width = max(x + 1, width)
            height = max(y + 1, height)
            x += 1
            if x > max_width - 1:
                x = 0
                y += 1
        return x, y, width, height

    @staticmethod
    def _ansi_rgb_to_style_color(rgb: Any, foreground: bool) -> Style:
        """Convert an ochre RGB color to a Rich Style color component."""
        color_str = (
            "rgb("
            + str(int(rgb.red * 255))
            + ","
            + str(int(rgb.green * 255))
            + ","
            + str(int(rgb.blue * 255))
            + ")"
        )
        if foreground:
            return Style.from_color(color=RichColor.parse(color_str))
        return Style.from_color(bgcolor=RichColor.parse(color_str))

    @staticmethod
    def _ansi_clear_line(
        document: "AnsiArtDocument",
        row: int,
        before: bool,
        after: bool,
        x_pos: int,
        default_style: Style,
    ) -> None:
        """Clear cells in a document row."""
        cols: List[int] = []
        if before:
            cols += range(len(document.ch[row]))
        if after:
            cols += range(x_pos, len(document.ch[row]))
        for col in cols:
            document.ch[row][col] = " "
            document.st[row][col] = default_style

    @staticmethod
    def _ansi_handle_clear(
        instruction: Any,
        document: "AnsiArtDocument",
        x: int,
        y: int,
        default_style: Style,
    ) -> "Tuple[int, int]":
        """Handle a stransi.SetClear instruction. Returns updated (x, y)."""
        import stransi.clear as _sc

        def cl(row: int, before: bool, after: bool) -> None:
            AnsiArtDocument._ansi_clear_line(
                document, row, before, after, x, default_style
            )

        region = instruction.region
        if region == _sc.Clear.LINE:
            cl(y, True, True)
        elif region == _sc.Clear.LINE_AFTER:
            cl(y, False, True)
        elif region == _sc.Clear.LINE_BEFORE:
            cl(y, True, False)
        elif region == _sc.Clear.SCREEN:
            for row in range(len(document.ch)):
                cl(row, True, True)
            x, y = 0, 0
        elif region == _sc.Clear.SCREEN_AFTER:
            for row in range(y, len(document.ch)):
                cl(row, row > y, True)
        elif region == _sc.Clear.SCREEN_BEFORE:
            for row in range(y):
                cl(row, True, row < y)
        return x, y

    @staticmethod
    def from_ansi(
        text: str,
        default_bg: str = "#ffffff",
        default_fg: str = "#000000",
        max_width: int = 100000,
    ) -> "AnsiArtDocument":
        """Creates a document from the given ANSI text."""
        # Currently uses stransi for ANSI parsing because Rich's API doesn't support
        # absolute cursor positioning (ESC[y;xH) needed for full ANSI art rendering.

        # Workaround for unwanted color rounding
        # RGB.__post_init__ rounds the color components, in decimal, causing 128 to become 127.
        from ochre.spaces import RGB

        RGB.__post_init__ = lambda self: None

        ansi = stransi.Ansi(text)
        default_style = Style(color=default_fg, bgcolor=default_bg)
        document = AnsiArtDocument(0, 0, default_bg, default_fg)
        width = 1
        height = 1
        x = 0
        y = 0
        current_style = default_style

        for instruction in ansi.instructions():
            if isinstance(instruction, str):
                for char in instruction:
                    x, y, width, height = AnsiArtDocument._ansi_handle_char(
                        char,
                        document,
                        x,
                        y,
                        width,
                        height,
                        current_style,
                        default_style,
                        max_width,
                    )
            elif (
                isinstance(instruction, stransi.SetColor)
                and instruction.color is not None
            ):
                # Color role: FOREGROUND or BACKGROUND
                is_fg = instruction.role == stransi.color.ColorRole.FOREGROUND
                current_style += AnsiArtDocument._ansi_rgb_to_style_color(
                    instruction.color.rgb, is_fg
                )
            elif isinstance(instruction, stransi.SetCursor):
                # stransi stores ESC[y;xH with x/y swapped — compensate by reading move.y as x.
                if instruction.move.relative:
                    x += instruction.move.y
                    y += instruction.move.x
                else:
                    x = instruction.move.y
                    y = instruction.move.x
                x = max(0, min(max_width - 1, x))
                y = max(0, y)
                width = max(x + 1, width)
                height = max(y + 1, height)
                while len(document.ch) <= y:
                    document.ch.append([])
                    document.st.append([])
            elif isinstance(instruction, stransi.SetClear):
                x, y = AnsiArtDocument._ansi_handle_clear(
                    instruction, document, x, y, default_style
                )
            elif isinstance(instruction, stransi.SetAttribute):
                pass  # attributes not rendered
            elif isinstance(instruction, stransi.Unsupported):
                raise ValueError("Unknown instruction " + repr(instruction.token))
            else:
                raise ValueError("Unknown instruction type " + str(type(instruction)))

        document.width = width
        document.height = height
        del document.ch[document.height :]
        del document.st[document.height :]
        while len(document.ch) < document.height:
            document.ch.append([])
            document.st.append([])
        for y in range(document.height):
            for _unused in range(len(document.ch[y]), document.width):
                document.ch[y].append(" ")
                document.st[y].append(default_style)
        return document

    @staticmethod
    def from_text(
        text: str, default_bg: str = "#ffffff", default_fg: str = "#000000"
    ) -> "AnsiArtDocument":
        """Creates a document from the given text, detecting if it uses ANSI control codes or not."""
        if ansi_detector_pattern.search(text):
            return AnsiArtDocument.from_ansi(text, default_bg, default_fg)
        else:
            return AnsiArtDocument.from_plain(text, default_bg, default_fg)

    @staticmethod
    def from_image_format(content: bytes) -> "AnsiArtDocument":
        """Creates a document from the given bytes, detecting the file format.

        Raises UnidentifiedImageError if the format is not detected.
        """
        image = Image.open(io.BytesIO(content))
        rgb_image = image.convert("RGB")  # handles indexed images, etc.
        width, height = rgb_image.size
        document = AnsiArtDocument(width, height)
        for y in range(height):
            for x in range(width):
                r, g, b = rgb_image.getpixel((x, y))  # type: ignore
                document.st[y][x] += Style.from_color(
                    bgcolor=RichColor.from_rgb(r, g, b)
                )
        return document

    @staticmethod
    def _svg_apply_stylesheets(root: "ET.Element") -> None:
        """Parse <style> elements and apply rules as inline attributes."""
        from textual.css.model import RuleSet
        from textual.css.parse import parse

        property_map = {"fill": "color"}
        reverse_property_map = {v: k for k, v in property_map.items()}

        def rewrite_property(match: "re.Match[str]") -> str:
            name, value = match.group(1), match.group(2)
            if name in property_map:
                return f"{property_map[name]}: {value}"
            return match.group(0)

        rule_sets: List[RuleSet] = []
        for style_el in root.findall(".//{http://www.w3.org/2000/svg}style"):
            assert style_el.text is not None, "style element has no text"
            css = re.sub(r"\s*@[\w-]+\s*{[^}]+}", "", style_el.text)
            css = re.sub(r"([\w-]+)\s*:\s*([^;}]+)", rewrite_property, css)
            rule_sets.extend(parse(scope="", css=css, read_from=("inline", "style")))

        for rule_set in rule_sets:
            rules = rule_set.styles.extract_rules((0, 0, 0))
            for css_selector in rule_set.selector_names:
                if css_selector.startswith("."):
                    xpath = f".//*[@class='{css_selector[1:]}']"
                elif css_selector.startswith("#"):
                    xpath = f".//*[@id='{css_selector[1:]}']"
                else:
                    xpath = ".//*[id='never-match-me-please']"
                for element in root.findall(xpath):
                    for prop, _specificity, value in rules:
                        prop = reverse_property_map.get(prop, prop)
                        if isinstance(value, str):
                            element.attrib[prop] = value
                        elif isinstance(value, Color):
                            element.attrib[prop] = value.hex

    @staticmethod
    def _svg_filter_container_rects(rects: "List[ET.Element]") -> "List[ET.Element]":
        """Remove rects that fully contain other rects (background/border frames)."""

        def rect_contains(outer: "ET.Element", inner: "ET.Element") -> bool:
            return (
                float(outer.attrib["x"]) <= float(inner.attrib["x"])
                and float(outer.attrib["y"]) <= float(inner.attrib["y"])
                and float(outer.attrib["x"]) + float(outer.attrib["width"])
                >= float(inner.attrib["x"]) + float(inner.attrib["width"])
                and float(outer.attrib["y"]) + float(outer.attrib["height"])
                >= float(inner.attrib["y"]) + float(inner.attrib["height"])
            )

        rects.sort(
            key=lambda r: float(r.attrib["width"]) * float(r.attrib["height"]),
            reverse=True,
        )
        to_ignore: Set[ET.Element] = set()
        for i, outer in enumerate(rects):
            outer_area = float(outer.attrib["width"]) * float(outer.attrib["height"])
            for inner in rects[i + 1 :]:
                inner_area = float(inner.attrib["width"]) * float(
                    inner.attrib["height"]
                )
                if inner_area > outer_area:
                    break
                if outer != inner and rect_contains(outer, inner):
                    to_ignore.add(outer)
                    if DEBUG_SVG_LOADING:
                        outer.attrib["style"] = (
                            "stroke:#ff0000;stroke-width:1;stroke-dasharray:1,1;fill:none"
                        )
        return [r for r in rects if r not in to_ignore]

    @staticmethod
    def _svg_compute_cell_size(
        rects: "List[ET.Element]",
        root: "ET.Element",
    ) -> "Tuple[float, float]":
        """Estimate cell width and height from rect positions using track analysis."""
        min_width = min(float(r.attrib["width"]) for r in rects)
        min_height = min(float(r.attrib["height"]) for r in rects)
        if min_width <= 0 or min_height <= 0:
            raise ValueError("SVG contains rects with zero or negative dimensions.")

        class Track(NamedTuple):
            rects: "List[ET.Element]"
            min_center: float
            max_center: float

        def join_tracks(t1: Track, t2: Track) -> Track:
            return Track(
                t1.rects + t2.rects,
                min(t1.min_center, t2.min_center),
                max(t1.max_center, t2.max_center),
            )

        def rect_center(rect: "ET.Element", coord: str, size: str) -> float:
            return float(rect.attrib[coord]) + float(rect.attrib[size]) / 2

        measures: Dict[str, float] = {}
        axes: List[Tuple[str, str, float]] = [
            ("x", "width", min_width),
            ("y", "height", min_height),
        ]
        for coord_attrib, size_attrib, min_rect_size in axes:
            rects.sort(key=lambda r: float(r.attrib[coord_attrib]))
            rects.sort(
                key=lambda r: float(r.attrib["x" if coord_attrib == "y" else "y"])
            )
            max_rects = 30
            max_rect_size = min_rect_size * 1.5
            tracks = [
                Track(
                    [r],
                    rect_center(r, coord_attrib, size_attrib),
                    rect_center(r, coord_attrib, size_attrib),
                )
                for r in rects[:max_rects]
                if float(r.attrib[size_attrib]) <= max_rect_size
            ]
            joined = True
            while joined and len(tracks) > 1:
                joined = False
                for i in range(len(tracks)):
                    for j in range(i + 1, len(tracks)):
                        max_offset = min_rect_size * 0.9
                        i_center = (tracks[i].min_center + tracks[i].max_center) / 2
                        j_center = (tracks[j].min_center + tracks[j].max_center) / 2
                        if abs(i_center - j_center) <= max_offset:
                            tracks[i] = join_tracks(tracks[i], tracks[j])
                            del tracks[j]
                            joined = True
                            break
                    if joined:
                        break
            tracks.sort(key=lambda t: (t.min_center + t.max_center) / 2)
            if DEBUG_SVG_LOADING:
                import defusedxml.ElementTree as ET

                for track in tracks:
                    ET.SubElement(
                        root,
                        "{http://www.w3.org/2000/svg}rect",
                        {
                            "x": str(track.min_center) if coord_attrib == "x" else "0",
                            "y": str(track.min_center) if coord_attrib == "y" else "0",
                            "width": (
                                str(track.max_center - track.min_center + 0.001)
                                if coord_attrib == "x"
                                else "100%"
                            ),
                            "height": (
                                str(track.max_center - track.min_center + 0.001)
                                if coord_attrib == "y"
                                else "100%"
                            ),
                            "style": "fill:#0000ff;fill-opacity:0.1;stroke:#0000ff;stroke-width:0.1",
                        },
                    )
            max_gap = min_rect_size * 2
            gaps: List[float] = []
            for i in range(len(tracks) - 1):
                i_center = (tracks[i].max_center + tracks[i].min_center) / 2
                j_center = (tracks[i + 1].max_center + tracks[i + 1].min_center) / 2
                gap = abs(j_center - i_center)
                if DEBUG_SVG_LOADING:
                    import defusedxml.ElementTree as ET2

                    ET2.SubElement(
                        root,
                        "{http://www.w3.org/2000/svg}line",
                        {
                            "x1": str(i_center)
                            if coord_attrib == "x"
                            else ("5%" if i % 2 == 0 else "2%"),
                            "y1": str(i_center)
                            if coord_attrib == "y"
                            else ("5%" if i % 2 == 0 else "2%"),
                            "x2": str(j_center)
                            if coord_attrib == "x"
                            else ("5%" if i % 2 == 0 else "2%"),
                            "y2": str(j_center)
                            if coord_attrib == "y"
                            else ("5%" if i % 2 == 0 else "2%"),
                            "stroke": "#ff0000" if gap > max_gap else "#0051ff",
                        },
                    )
                if gap <= max_gap:
                    gaps.append(gap)
            measures[coord_attrib] = sum(gaps) / len(gaps) if gaps else min_rect_size

        return measures["x"], measures["y"]

    @staticmethod
    def _svg_get_fill(el: "ET.Element") -> "Optional[str]":
        """Extract and normalize the fill color from an SVG element, or None."""
        fill = el.attrib.get("fill")
        if fill is None:
            style = el.attrib.get("style", "")
            for part in style.split(";"):
                if part.startswith("fill:"):
                    fill = part[len("fill:") :]
                    break
            else:
                import defusedxml.ElementTree as ET

                print(
                    "Warning: element has no fill or style attribute: "
                    + ET.tostring(el, encoding="unicode")
                )
        if not fill or fill == "none":
            import defusedxml.ElementTree as ET

            print(
                "Warning: element has no fill defined: "
                + ET.tostring(el, encoding="unicode")
            )
            return None
        try:
            r, g, b = Color.parse(fill).rgb
            return "#" + hex(r)[2:].zfill(2) + hex(g)[2:].zfill(2) + hex(b)[2:].zfill(2)
        except ColorParseError:
            import defusedxml.ElementTree as ET

            print(
                "Warning: element has invalid fill: "
                + ET.tostring(el, encoding="unicode")
            )
            return None

    @staticmethod
    def _svg_fill_background(
        document: "AnsiArtDocument",
        rects: "List[ET.Element]",
        cell_width: float,
        cell_height: float,
        min_x: float,
        min_y: float,
        add_debug_marker: "Any",
    ) -> None:
        """Fill document cells with background colors from rect elements."""
        for rect in rects:
            fill = AnsiArtDocument._svg_get_fill(rect)
            for x_offset in range(
                int(float(rect.attrib["width"]) / cell_width + 1 / 2)
            ):
                for y_offset in range(
                    int(float(rect.attrib["height"]) / cell_height + 1 / 2)
                ):
                    rx = float(rect.attrib["x"]) + cell_width * (x_offset + 1 / 2)
                    ry = float(rect.attrib["y"]) + cell_height * (y_offset + 1 / 2)
                    add_debug_marker(rx, ry, "red")
                    cx = int((rx - min_x) / cell_width)
                    cy = int((ry - min_y) / cell_height)
                    if fill is not None:
                        try:
                            document.st[cy][cx] += Style.from_color(
                                bgcolor=RichColor.parse(fill)
                            )
                        except IndexError:
                            print(
                                "Warning: rect out of bounds: "
                                + ET.tostring(rect, encoding="unicode")
                            )

    @staticmethod
    def _svg_apply_texts(
        document: "AnsiArtDocument",
        root: "ET.Element",
        cell_width: float,
        cell_height: float,
        min_x: float,
        min_y: float,
        add_debug_marker: "Any",
    ) -> None:
        """Apply text elements to document cells."""
        texts = root.findall(".//{http://www.w3.org/2000/svg}text")
        if len(texts) == 0:
            raise ValueError("No text elements found in SVG.")
        for text in texts:
            tx = float(text.attrib["x"]) + cell_width / 2
            ty = float(text.attrib["y"]) - cell_height / 4
            add_debug_marker(tx, ty, "yellow")
            cx = int((tx - min_x) / cell_width)
            cy = int((ty - min_y) / cell_height)
            ch = text.text
            if ch is None:
                tspans = text.findall(".//{http://www.w3.org/2000/svg}tspan")
                if not tspans:
                    print(
                        "Warning: text element has no text or tspan: "
                        + ET.tostring(text, encoding="unicode")
                    )
                    continue
                ch = ""
                for tspan in tspans:
                    if tspan.text is not None:
                        ch += tspan.text
                    else:
                        print(
                            "Warning: tspan element has no text: "
                            + ET.tostring(tspan, encoding="unicode")
                        )
            fill = AnsiArtDocument._svg_get_fill(text)
            try:
                document.ch[cy][cx] = ch
                if fill is not None:
                    document.st[cy][cx] += Style.from_color(color=RichColor.parse(fill))
            except IndexError:
                print(
                    "Warning: text element is out of bounds: "
                    + ET.tostring(text, encoding="unicode")
                )

    @staticmethod
    def from_svg(
        svg: str, default_bg: str = "#ffffff", default_fg: str = "#000000"
    ) -> "AnsiArtDocument":
        """Creates a document from an SVG containing a character grid with rects for cell backgrounds.

        - If the SVG contains a special <ansi> element, this is used instead of anything else.
        Otherwise it falls back to flexible grid detection:
        - rect elements can be in any order, in different groups, and vary in size.
        - rect elements can be missing (default background used) or outside the grid.
        - fill OR style attributes are used for background/foreground colors.
        - stylesheets are partially supported.
        """

        root = ET.fromstring(svg)

        ansi_el = root.find(".//{http://github.com/1j01/textual-paint}ansi")
        if ansi_el is not None:
            if ansi_el.text is None:
                return AnsiArtDocument(1, 1, default_bg, default_fg)
            return AnsiArtDocument.from_ansi(
                base64.b64decode(ansi_el.text).decode("utf-8"), default_bg, default_fg
            )

        def add_debug_marker(x: float, y: float, color: str) -> None:
            if not DEBUG_SVG_LOADING:
                return
            marker = ET.Element("{http://www.w3.org/2000/svg}circle")
            marker.attrib.update(
                {
                    "cx": str(x),
                    "cy": str(y),
                    "r": "1",
                    "fill": color,
                    "stroke": "black",
                    "stroke-width": "0.1",
                }
            )
            root.append(marker)

        AnsiArtDocument._svg_apply_stylesheets(root)

        rects = root.findall(".//{http://www.w3.org/2000/svg}rect")
        if not rects:
            raise ValueError("No rect elements found in SVG.")

        rects = AnsiArtDocument._svg_filter_container_rects(rects)
        assert len(rects) > 0, (
            "No rect elements after removing rects containing other rects."
        )

        cell_width, cell_height = AnsiArtDocument._svg_compute_cell_size(rects, root)
        print("Initial cell size guess: " + str(cell_width) + " x " + str(cell_height))

        min_x = min(float(r.attrib["x"]) for r in rects)
        min_y = min(float(r.attrib["y"]) for r in rects)
        max_x = max(float(r.attrib["x"]) + float(r.attrib["width"]) for r in rects)
        max_y = max(float(r.attrib["y"]) + float(r.attrib["height"]) for r in rects)
        add_debug_marker(min_x, min_y, "blue")
        add_debug_marker(max_x, max_y, "blue")

        width = int((max_x - min_x) / cell_width + 1 / 9)
        height = int((max_y - min_y) / cell_height + 1 / 9)
        cell_width = (max_x - min_x) / width
        cell_height = (max_y - min_y) / height
        print(
            "Refined cell size estimate: " + str(cell_width) + " x " + str(cell_height)
        )

        document = AnsiArtDocument(width, height, default_bg, default_fg)
        AnsiArtDocument._svg_fill_background(
            document, rects, cell_width, cell_height, min_x, min_y, add_debug_marker
        )
        AnsiArtDocument._svg_apply_texts(
            document, root, cell_width, cell_height, min_x, min_y, add_debug_marker
        )

        if DEBUG_SVG_LOADING:
            ET.ElementTree(root).write("debug.svg", encoding="unicode")

        return document

    @staticmethod
    def decode_based_on_file_extension(
        content: bytes,
        file_path: str,
        default_bg: str = "#ffffff",
        default_fg: str = "#000000",
    ) -> "AnsiArtDocument":
        """Creates a document from the given bytes, detecting the file format.

        Raises FormatReadNotSupported if the file format is not supported for reading. Some are write-only.
        Raises UnicodeDecodeError, which can be a very long message, so make sure to handle it!
        Raises UnidentifiedImageError if the format is not detected.
        """
        format_id = AnsiArtDocument.format_from_extension(file_path)
        # Try image formats first; fall back to text-based formats.
        # This also handles image files without recognized extensions.
        if format_id in Image.OPEN:
            return AnsiArtDocument.from_image_format(content)
        # Try as image even if the extension is unknown, before falling through to text.
        if format_id is None:
            try:
                return AnsiArtDocument.from_image_format(content)
            except Exception:
                pass  # Not an image; continue to text-based formats
        if format_id == "ANSI":
            return AnsiArtDocument.from_ansi(
                content.decode("utf-8"), default_bg, default_fg
            )
        elif format_id == "IRC":
            return AnsiArtDocument.from_irc(
                content.decode("utf-8"), default_bg, default_fg
            )
        elif format_id == "PLAINTEXT":
            return AnsiArtDocument.from_plain(
                content.decode("utf-8"), default_bg, default_fg
            )
        elif format_id == "SVG":
            return AnsiArtDocument.from_svg(
                content.decode("utf-8"), default_bg, default_fg
            )
        elif format_id in Image.SAVE or format_id in ["HTML", "RICH_CONSOLE_MARKUP"]:
            # This is a write-only format.
            raise FormatReadNotSupported(
                localized_message=_("Cannot read files saved as %1 format.", format_id)
            )
        else:
            # This is an unknown format.
            # For now at least, I'm preserving the behavior of loading as ANSI/PLAINTEXT.
            return AnsiArtDocument.from_text(
                content.decode("utf-8"), default_bg, default_fg
            )


class Selection:
    """
    A selection within an AnsiArtDocument.

    AnsiArtDocument can contain a Selection, and Selection can contain an AnsiArtDocument.
    However, the selection's AnsiArtDocument should never itself contain a Selection.

    When a selection is created, it has no image data, but once it's dragged,
    it gets a copy of the image data from the document.
    The image data is stored as an AnsiArtDocument, since it's made up of characters and colors.
    """

    def __init__(self, region: Region) -> None:
        """Initialize a selection."""

        self.region: Region = region
        """The region of the selection within the outer document."""

        self.contained_image: Optional[AnsiArtDocument] = None
        """The image data contained in the selection, None until dragged, except for text boxes."""

        self.pasted: bool = False
        """Whether the selection was pasted from the clipboard, and thus needs an undo state created for it when melding."""

        self.textbox_mode = False
        """Whether the selection is a text box OR A CURSOR. Regardless, it's always text, but there are different editing modes."""

        self.cursor_mode = False
        """Whether the selection is a cursor. I'm probably shoehorning too much into "Selection"."""

        self.textbox_edited = False
        """Whether text has been typed into the text box, ever. If not, the textbox can be deleted when clicking off."""

        self.text_selection_start = Offset(0, 0)
        """The start position of the text selection within the text box. This may be before or after the end.""" ""

        self.text_selection_end = Offset(0, 0)
        """The end position of the text selection within the text box. This may be before or after the start.""" ""

        self.mask: Optional[List[List[bool]]] = None
        """A mask of the selection to cut out, used for Free-Form Select tool. Coordinates are relative to the selection region."""

    def copy_from_document(self, document: "AnsiArtDocument") -> None:
        """Copy the image data from the document into the selection."""
        self.contained_image = AnsiArtDocument(self.region.width, self.region.height)
        self.contained_image.copy_region(source=document, source_region=self.region)

    def copy_to_document(
        self, document: "AnsiArtDocument", transparent: bool = False
    ) -> None:
        """Draw the selection onto the document.

        Args:
            document: Target document to draw onto
            transparent: If True, skip spaces (transparent mode)
        """
        if not self.contained_image:
            return

        target_region = self.region.intersection(
            Region(0, 0, document.width, document.height)
        )
        source_region = Region(
            target_region.x - self.region.x,
            target_region.y - self.region.y,
            self.contained_image.width,
            self.contained_image.height,
        )

        offset = target_region.offset - self.region.offset
        if self.mask:

            def sample(x: int, y: int) -> bool:
                assert self.mask is not None
                try:
                    return self.mask[y + offset.y][x + offset.x]
                except IndexError:
                    return False

            mask = [
                [sample(x, y) for x in range(source_region.width)]
                for y in range(source_region.height)
            ]
        else:
            mask = None

        document.copy_region(
            source=self.contained_image,
            source_region=source_region,
            target_region=target_region,
            mask=mask,
            transparent=transparent,
        )
