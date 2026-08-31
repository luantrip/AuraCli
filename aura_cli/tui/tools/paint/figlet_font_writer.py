"""FIGlet Font Writer - Aura CLI Paint Tool

Write FIGlet font (.flf) files with automatic corrections.

Features:
    - Generate .flf file data from character definitions
    - Auto-fix character widths and heights
    - Generate missing lowercase characters from uppercase
    - Support for layout modes (full, fitted, smushing)
    - Required ASCII + Deutsch character set (102 chars)
    - Based on patorjk.com/figlet-editor

Author: Patrick Gillespie
Maintainer: Isaiah Odhner
License: MIT
"""

from enum import Enum
from typing import ClassVar, Dict, List


class FIGletFontWriter:
    """FIGlet font file generator with auto-correction.

    Generates .flf file data from character definitions, automatically
    fixing common issues like incorrect dimensions and missing characters.

    Attributes:
        charOrder: Required character codes (ASCII 32-126 + Deutsch chars)

    Methods:
        createFigFileData: Generate complete .flf file content
    """

    class Layout(Enum):
        """FIGcharacter spacing layout modes.

        Attributes:
            FULL: Full width/height spacing (no overlap)
            FITTED: Characters touch but don't overlap
            UNIVERSAL_SMUSHING: Overlap by one, latter char takes precedence
            CONTROLLED_SMUSHING: Overlap with configurable rules
        """

        FULL = 0
        FITTED = 1
        UNIVERSAL_SMUSHING = 2
        CONTROLLED_SMUSHING = 3

    charOrder: ClassVar[List[int]] = [
        *list(range(32, 127)),
        196,
        214,
        220,
        228,
        246,
        252,
        223,
    ]
    """Required character codes for FIGlet fonts (102 total).

    Includes ASCII 32-126 (printable chars) plus Deutsch umlauts:
    Ä(196), Ö(214), Ü(220), ä(228), ö(246), ü(252), ß(223)

    Additional characters must use code tagged characters, which are not yet supported.
    """

    def __init__(
        self,
        figChars: Dict[int, str] | None = None,
        height: int | None = None,
        baseline: int | None = None,
        maxLength: int | None = None,
        commentLines: List[str] | None = None,
        rightToLeft: bool = False,
        horizontalLayout: Layout = Layout.UNIVERSAL_SMUSHING,
        verticalLayout: Layout = Layout.UNIVERSAL_SMUSHING,
        codeTagCount: int = 0,
        hardBlank: str = "$",
        endMark: str = "@",
        caseInsensitive: bool = False,
    ) -> None:
        """Create a new FIGletFontWriter.

        All parameters are optional and can be set later. Validation runs
        at construction and again when createFigFileData() is called.

        Args:
            figChars: Maps character codes to FIGcharacter strings. Defaults to {}.
            height: FIGcharacter height in sub-characters. Auto-calculated if None.
            baseline: Distance from top to baseline. Defaults to height if None.
            maxLength: Max line length including two endMark characters. Auto-calculated if None.
            commentLines: Informational header lines (recommended: font name + author).
            rightToLeft: RTL writing direction. Defaults to False.
            horizontalLayout: FIGcharacter spacing mode. Defaults to UNIVERSAL_SMUSHING.
            verticalLayout: FIGcharacter spacing mode. Defaults to UNIVERSAL_SMUSHING.
            codeTagCount: Extra tagged FIGcharacters beyond the required 102. Defaults to 0.
            hardBlank: Space-like char that prevents smushing. Defaults to "$".
            endMark: Line-end marker character. Defaults to "@".
            caseInsensitive: Overwrites lowercase with uppercase copies. Defaults to False.

        Raises:
            ValueError: If any parameter value is invalid.
        """

        if commentLines is None:
            commentLines = []
        if figChars is None:
            figChars = {}
        self.figChars: Dict[int, str] = figChars
        """Dictionary that maps character codes to FIGcharacter strings."""

        self.height = height
        """Height of a FIGcharacter, in sub-characters."""

        self.baseline = baseline
        """Distance from the top of the FIGcharacter to the baseline. If not specified, defaults to height."""

        self.maxLength = maxLength
        """Maximum length of a line INCLUDING two endMark characters."""

        self.commentLines: List[str] = commentLines
        """List of comment lines to be included in the header. It's recommended to include at least the name of the font and the name of the author."""

        self.rightToLeft = rightToLeft
        """Indicates RTL writing direction (or LTR if False)."""

        self.codeTagCount = codeTagCount
        """Number of extra FIGcharacters included in the font (in addition to the required 102 untagged characters). Outputting tagged characters is not yet supported."""

        self.hardBlank = hardBlank
        """Character rendered as a space which can prevent smushing."""

        self.endMark = endMark
        """Denotes the end of a line. Two of these characters in a row denotes the end of a FIGcharacter."""

        self.horizontalLayout = horizontalLayout
        """Defines how FIGcharacters are spaced horizontally."""

        self.verticalLayout = verticalLayout
        """Defines how FIGcharacters are spaced vertically."""

        self.hRule = [False] * 7
        """Horizontal Smushing Rules, 1-6 (0 is not used, so that indices correspond with the names of the parameters).

        horizontalLayout must be Layout.CONTROLLED_SMUSHING for these to take effect."""

        self.vRule = [False] * 6
        """Vertical Smushing Rules, 1-5 (0 is not used, so that indices correspond with the names of the parameters).

        verticalLayout must be Layout.CONTROLLED_SMUSHING for these to take effect."""

        self.caseInsensitive = caseInsensitive
        """Makes lowercase same as uppercase. Note that this is one-way overwrite. It doesn't check if a character already exists, and it won't fill in uppercase using lowercase."""

        self._validateOptions()

    def _validateOptions(self) -> None:
        """Validate font parameters.

        Raises:
            ValueError: If parameters are invalid
            NotImplementedError: If codeTagCount is non-zero

        Note:
            Called on init and before generating font file.
            See _fixFigChars() for active corrections.
        """
        if self.horizontalLayout not in list(self.Layout):
            raise ValueError(
                f"Invalid horizontalLayout: {self.horizontalLayout!r} ({type(self.horizontalLayout)})"
            )
        if self.verticalLayout not in list(self.Layout):
            raise ValueError(
                f"Invalid verticalLayout: {self.verticalLayout!r} ({type(self.verticalLayout)})"
            )
        # Check sentinel values
        if self.hardBlank == self.endMark:
            raise ValueError(
                f"hardBlank and endMark cannot be the same character: {self.hardBlank!r}"
            )
        if len(self.endMark) != 1:
            raise ValueError(f"endMark must be a single character: {self.endMark!r}")
        if len(self.hardBlank) != 1:
            raise ValueError(
                f"hardBlank must be a single character: {self.hardBlank!r}"
            )
        # Check there's no newlines in the comment lines
        for line in self.commentLines:
            if "\n" in line:
                raise ValueError(
                    f"Strings in commentLines cannot contain newlines: {line!r}"
                )
        # Check codeTagCount
        if self.codeTagCount != 0:
            raise NotImplementedError("codeTagCount is not yet supported")

    def _getOldLayoutValue(self) -> int:
        """Calculate old layout value for backward compatibility.

        Returns:
            Integer encoding horizontal layout and smushing rules
        """
        val = 0
        if self.horizontalLayout == self.Layout.FULL:
            return -1
        elif (
            self.horizontalLayout == self.Layout.FITTED
            or self.horizontalLayout == self.Layout.UNIVERSAL_SMUSHING
        ):
            return 0
        else:
            val += 1 if self.hRule[1] else 0
            val += 2 if self.hRule[2] else 0
            val += 4 if self.hRule[3] else 0
            val += 8 if self.hRule[4] else 0
            val += 16 if self.hRule[5] else 0
            val += 32 if self.hRule[6] else 0
        return val

    def _getFullLayoutValue(self) -> int:
        """Calculate full layout value with horizontal and vertical rules.

        Returns:
            Integer encoding both horizontal and vertical layout settings
        """
        val = 0

        # horizontal rules
        if self.horizontalLayout == self.Layout.FULL:
            val += 0
        elif self.horizontalLayout == self.Layout.FITTED:
            val += 64
        elif self.horizontalLayout == self.Layout.UNIVERSAL_SMUSHING:
            val += 128
        else:
            val += 128
            val += 1 if self.hRule[1] else 0
            val += 2 if self.hRule[2] else 0
            val += 4 if self.hRule[3] else 0
            val += 8 if self.hRule[4] else 0
            val += 16 if self.hRule[5] else 0
            val += 32 if self.hRule[6] else 0

        # vertical rules
        if self.verticalLayout == self.Layout.FULL:
            val += 0
        elif self.verticalLayout == self.Layout.FITTED:
            val += 8192
        elif self.verticalLayout == self.Layout.UNIVERSAL_SMUSHING:
            val += 16384
        else:
            val += 16384
            val += 256 if self.vRule[1] else 0
            val += 512 if self.vRule[2] else 0
            val += 1024 if self.vRule[3] else 0
            val += 2048 if self.vRule[4] else 0
            val += 4096 if self.vRule[5] else 0

        return val

    def _generateFigFontHeader(self) -> str:
        """Generate FIGlet font file header line.

        Returns:
            Space-separated header string with font metadata

        Raises:
            ValueError: If height is not specified
        """
        header: List[str] = []
        baseline = self.baseline

        if self.height is None:
            raise ValueError(
                "Height must be specified, or should be automatically determined."
            )
        if baseline is None:
            baseline = self.height
        baseline = int(baseline)
        if baseline <= 0 or baseline > self.height:
            baseline = self.height

        header.append("flf2a" + self.hardBlank)
        header.append(str(self.height))
        header.append(str(baseline))
        header.append(str(self.maxLength))
        header.append(str(self._getOldLayoutValue()))
        header.append(str(len(self.commentLines)))
        header.append("1" if self.rightToLeft else "0")
        header.append(str(self._getFullLayoutValue()))
        header.append(str(self.codeTagCount))

        return " ".join(header)

    def _fixFigChars(self) -> None:
        """Auto-correct FIGcharacter dimensions and case.

        Ensures:
        - Consistent height across all characters
        - Consistent width within each character
        - Lowercase copies uppercase if caseInsensitive=True
        - Proper padding for shorter lines/characters

        Note:
            Updates self.height and self.maxLength automatically.
        """
        height = 0
        charWidth: Dict[int, int] = {}
        maxWidth = 0

        if self.caseInsensitive is True:
            for ii in range(97, 123):
                self.figChars[ii] = self.figChars[ii - 32]

        for idx in self.figChars:
            figChar = self.figChars[idx].replace("\r\n", "\n").split("\n")
            height = max(height, len(figChar))
            charWidth[idx] = 0

            for line in figChar:
                charWidth[idx] = max(charWidth[idx], len(line))

            for i in range(len(figChar)):
                if len(figChar[i]) < charWidth[idx]:
                    figChar[i] += " " * (charWidth[idx] - len(figChar[i]))

                maxWidth = max(maxWidth, charWidth[idx])

            self.figChars[idx] = "\n".join(figChar)

        for idx in self.figChars:
            figChar = self.figChars[idx].replace("\r\n", "\n").split("\n")
            if len(figChar) < height:
                blankLines = [
                    " " * charWidth[idx] for _ in range(height - len(figChar))
                ]
                self.figChars[idx] = "\n".join(figChar) + "\n" + "\n".join(blankLines)

        self.height = height
        self.maxLength = maxWidth + 2

    def createFigFileData(self) -> str:
        """Generate complete FIGlet .flf file content.

        Returns:
            String containing full .flf file data ready to write

        Raises:
            ValueError: If validation fails
            Exception: If required character is missing from figChars

        Note:
            Validates options and fixes FIGcharacters before generation.
        """
        self._validateOptions()
        self._fixFigChars()

        output = self._generateFigFontHeader() + "\n"
        output += "\n".join(self.commentLines) + "\n"

        for char in self.charOrder:
            figChar = self.figChars.get(char)
            if figChar is None:
                raise Exception(f"Character {char} missing from figChars")
            output += (self.endMark + "\n").join(figChar.split("\n"))
            output += self.endMark + self.endMark + "\n"

        return output


__all__ = ["FIGletFontWriter"]
