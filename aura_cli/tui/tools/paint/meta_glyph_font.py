"""Meta Glyph Font System - Aura CLI Paint Tool.

Font system for rendering large text characters using smaller characters
via FIGlet font files.

Features:
    - FIGlet font file loading (.flf)
    - Meta-glyph rendering (characters made of characters)
    - Multiple font sizes (2x2, 4x4)
    - Automatic font size selection
    - Character coverage filtering
"""

import os
from typing import Dict, List

from pyfiglet import Figlet, FigletFont  # type: ignore


class MetaGlyphFont:
    """Font where each character is drawn with sub-characters.

    Loads FIGlet fonts and provides meta-glyph rendering where
    each character is composed of smaller characters.

    Attributes:
        file_path: Path to FIGlet font file
        glyphs: Map of characters to meta-glyph rows
        width: Meta-glyph width in characters
        height: Meta-glyph height in characters
        covered_characters: Characters supported by font
    """

    def __init__(
        self, file_path: str, width: int, height: int, covered_characters: str
    ):
        """Initialize meta glyph font.

        Args:
            file_path: Path to .flf FIGlet font file
            width: Glyph width in characters
            height: Glyph height in characters
            covered_characters: Characters to load from font
        """
        self.file_path = file_path
        self.glyphs: Dict[str, List[str]] = {}
        self.width = width
        self.height = height
        self.covered_characters = covered_characters

        for ch in " ░▒▓██▔🮂🮃▀🮄🮅🮆▇▆▅▄▃▂▁▏▎▍▌▋▊▉███🮋🮊🮉▐🮈🮇▕":
            self.covered_characters = self.covered_characters.replace(ch, "")

        self.load()

    def load(self):
        """Load font from FIGlet font file.

        Parses .flf file and generates meta-glyphs for all
        covered characters.
        """
        with open(self.file_path, encoding="utf-8") as f:
            flf = f.read()
            fig_font = FigletFont()
            fig_font.data = flf
            fig_font.loadFont()
            fig = Figlet()
            fig.font = self.file_path
            fig.Font = fig_font
            for char in self.covered_characters:
                meta_glyph = fig.renderText(char)
                self.glyphs[char] = meta_glyph.split("\n")


covered_characters = R""" !"#$%&'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]^_`abcdefghijklmnopqrstuvwxyz{|}~"""

meta_glyph_fonts: Dict[int, MetaGlyphFont] = {
    2: MetaGlyphFont(
        os.path.join(os.path.dirname(__file__), "fonts/NanoTiny/NanoTiny_v14_2x2.flf"),
        2,
        2,
        covered_characters,
    ),
}


def largest_font_that_fits(max_width: int, max_height: int) -> MetaGlyphFont | None:
    """Get largest font with glyphs fitting in dimensions.

    Args:
        max_width: Maximum glyph width
        max_height: Maximum glyph height

    Returns:
        Largest fitting font or None
    """
    for font_size in sorted(meta_glyph_fonts.keys(), reverse=True):
        font = meta_glyph_fonts[font_size]
        if font.width <= max_width and font.height <= max_height:
            return font
    return None
