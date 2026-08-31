"""AuraPaint integration for AuraCli.

Provides integration points for the native AuraPaint editor with other tools.

Features:
    - File Manager → Paint: Open ANSI art files
    - Paint → Export: Generate art from text/images
    - Cross-tool messaging system
    - ANSI art preview widget
    - Art generation utilities

Classes:
    OpenInPaint: Message to open file in Paint
    PaintPreviewRequest: Message to request ANSI preview
    ExportFromPaint: Message when art is exported
    AnsiArtPreview: Widget for previewing ANSI art
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Optional

try:
    from pyfiglet import Figlet
except ImportError:
    Figlet = None

from textual.message import Message
from textual.widget import Widget

try:
    from tree_sitter import Language, Parser
    import tree_sitter_python as tspython
except ImportError:
    Language = None
    Parser = None
    tspython = None

if TYPE_CHECKING:
    from aura_cli.application.paint.ansi_art_document import AnsiArtDocument


# ═══════════════════════════════════════════════════════════════════════════════
# Messages for Cross-Tool Communication
# ═══════════════════════════════════════════════════════════════════════════════


class OpenInPaint(Message):
    """Message to open a file in the Paint tool."""

    def __init__(self, file_path: Path) -> None:
        super().__init__()
        self.file_path = file_path


class PaintPreviewRequest(Message):
    """Message to request a preview of ANSI art content."""

    def __init__(self, content: str, callback: Optional[Callable] = None) -> None:
        super().__init__()
        self.content = content
        self.callback = callback


class ExportFromPaint(Message):
    """Message when art is exported from Paint."""

    def __init__(self, file_path: Path, output_format: str) -> None:
        super().__init__()
        self.file_path = file_path
        self.format = output_format


# ═══════════════════════════════════════════════════════════════════════════════
# ANSI Art Preview Widget
# ═══════════════════════════════════════════════════════════════════════════════


class AnsiArtPreview(Widget):
    """Widget for visualising ANSI art."""

    DEFAULT_CSS = """
    AnsiArtPreview {
        width: 100%;
        height: 100%;
        background: $surface;
        border: solid $primary;
        overflow: auto;
    }

    AnsiArtPreview .preview-content {
        width: auto;
        height: auto;
        padding: 1;
    }

    AnsiArtPreview .preview-header {
        width: 100%;
        height: 2;
        background: $panel;
        border-bottom: solid $primary;
        padding: 0 1;
    }
    """

    def __init__(self, content: str = "", file_path: Optional[Path] = None, **kwargs):
        super().__init__(**kwargs)
        self.content = content
        self.file_path = file_path
        self._document: Optional[AnsiArtDocument] = None

    def compose(self):
        from textual.containers import Vertical, VerticalScroll
        from textual.widgets import Static

        title = (
            f"Visualização: {self.file_path.name}"
            if self.file_path
            else "Visualização de Arte ANSI"
        )

        with Vertical():
            yield Static(title, classes="preview-header")
            with VerticalScroll():
                yield Static(
                    self.content, classes="preview-content", id="preview-content"
                )

    def update_content(self, content: str) -> None:
        """Update the preview content."""
        self.content = content
        try:
            preview = self.query_one("#preview-content")
            preview.update(content)
        except Exception as error:
            self.log.debug("Paint preview content is not mounted yet: %s", error)

    def load_file(self, file_path: Path) -> bool:
        """Load an ANSI art file for preview."""
        try:
            from aura_cli.application.paint.ansi_art_document import AnsiArtDocument

            self.file_path = file_path

            # Try to load as ANSI art
            doc = AnsiArtDocument(80, 24)
            content = file_path.read_text(encoding="utf-8", errors="replace")

            # Decode based on file type
            format_id = AnsiArtDocument.format_from_extension(str(file_path))
            if format_id:
                doc.decode_based_on_file_extension(
                    file_path.read_bytes(), str(file_path)
                )
                self._document = doc

                # Convert to displayable text
                self.content = self._render_document(doc)
                self.update_content(self.content)
                return True
            else:
                # Plain text fallback
                self.content = content
                self.update_content(self.content)
                return True

        except Exception as e:
            self.content = f"Error loading file: {e}"
            self.update_content(self.content)
            return False

    def _render_document(self, doc: AnsiArtDocument) -> str:
        """Render an AnsiArtDocument to a string with Rich markup."""
        from rich.text import Text

        lines = []
        for y in range(doc.height):
            line = Text()
            for x in range(doc.width):
                ch = doc.ch[y][x]
                style = doc.st[y][x]
                line.append(ch, style=style)
            lines.append(str(line))

        return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════════════
# Art Generation from Code/Data
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class ArtGenerationOptions:
    """Options for generating art from code/data."""

    width: int = 80
    height: int = 24
    style: str = "default"  # For from_image and from_code_structure
    font: str = "standard"  # For from_text (pyfiglet font)
    colors: str = "full"  # full, limited, mono


class ArtGenerator:
    """Generate ANSI art from various data sources."""

    # Character sets for different styles
    CHAR_SETS: ClassVar[dict] = {
        "default": "█▓▒░ ",
        "retro": "█▀▄▌▐░ ",
        "blocks": "█▇▆▅▄▃▂▁ ",
        "ascii": "#@%*+=-:. ",
        "dots": "⣿⣾⣷⣶⣵⣴⣳⣲⣱⣰ ",
        "minimal": "█ ",
    }

    # Color palettes
    PALETTES: ClassVar[dict] = {
        "full": None,  # Use any color
        "retro": [
            "#000000",
            "#800000",
            "#008000",
            "#808000",
            "#000080",
            "#800080",
            "#008080",
            "#c0c0c0",
            "#808080",
            "#ff0000",
            "#00ff00",
            "#ffff00",
            "#0000ff",
            "#ff00ff",
            "#00ffff",
            "#ffffff",
        ],
        "mono": ["#000000", "#ffffff"],
        "green": ["#000000", "#003300", "#006600", "#009900", "#00cc00", "#00ff00"],
    }

    @classmethod
    def from_image(
        cls, image_path: Path, options: Optional[ArtGenerationOptions] = None
    ) -> Optional[AnsiArtDocument]:
        """Generate ANSI art from an image file."""
        try:
            from PIL import Image
            from rich.style import Style

            from aura_cli.application.paint.ansi_art_document import AnsiArtDocument

            options = options or ArtGenerationOptions()

            # Load and resize image
            img = Image.open(image_path)
            img = img.convert("RGB")
            img = img.resize((options.width, options.height))

            # Create document
            doc = AnsiArtDocument(options.width, options.height)

            # Get character set
            chars = cls.CHAR_SETS.get(options.style, cls.CHAR_SETS["default"])

            # Convert pixels to characters
            for y in range(options.height):
                for x in range(options.width):
                    r, g, b = img.getpixel((x, y))

                    # Calculate brightness
                    brightness = (r + g + b) / 3 / 255

                    # Map to character
                    char_idx = int(brightness * (len(chars) - 1))
                    ch = chars[char_idx]

                    # Set color
                    color = f"#{r:02x}{g:02x}{b:02x}"
                    doc.ch[y][x] = ch
                    doc.st[y][x] = Style(color=color, bgcolor="#000000")

            return doc

        except Exception as e:
            print(f"Error generating art from image: {e}")
            return None

    @classmethod
    def from_text(
        cls, text: str, options: Optional[ArtGenerationOptions] = None
    ) -> Optional[AnsiArtDocument]:
        """Generate ANSI art banner from text using pyfiglet."""
        try:
            from rich.style import Style

            from aura_cli.application.paint.ansi_art_document import AnsiArtDocument

            options = options or ArtGenerationOptions()

            # Use pyfiglet for robust text-to-art conversion
            try:
                figlet = Figlet(font=options.style, width=options.width)
            except Exception:
                print(
                    f"Warning: Font '{options.style}' not found. Falling back to 'standard'."
                )
                figlet = Figlet(font="standard", width=options.width)

            rendered_text = figlet.renderText(text)
            lines = rendered_text.split("\n")

            # Calculate dimensions
            height = len(lines)
            width = max(len(line) for line in lines) if lines else 0

            if width == 0 or height == 0:
                return AnsiArtDocument(0, 0)

            # Create document
            doc = AnsiArtDocument(width, height, "#000000", "#00ff00")

            # Render text into document
            for y, line in enumerate(lines):
                for x, char in enumerate(line):
                    if y < doc.height and x < doc.width:
                        doc.ch[y][x] = char
                        doc.st[y][x] = Style(color="#00ff00", bgcolor="#000000")

            return doc

        except Exception as e:
            print(f"Error generating text art: {e}")
            return None

    @classmethod
    def from_code_structure(
        cls,
        code: str,
        language: str = "python",
        options: Optional[ArtGenerationOptions] = None,
    ) -> Optional[AnsiArtDocument]:
        """Generate a visual representation of code structure using tree-sitter."""
        try:
            from rich.style import Style

            from aura_cli.application.paint.ansi_art_document import AnsiArtDocument

            options = options or ArtGenerationOptions()

            structures = []
            if language == "python":
                PY_LANGUAGE = Language(tspython.language())
                parser = Parser(PY_LANGUAGE)
                tree = parser.parse(bytes(code, "utf8"))

                query_string = """
                (class_definition name: (identifier) @class.name)
                (function_definition name: (identifier) @function.name)
                """
                query = PY_LANGUAGE.query(query_string)
                captures = query.captures(tree.root_node)

                for node, capture_name in captures:
                    struct_type = (
                        "class" if capture_name == "class.name" else "function"
                    )
                    name = node.text.decode("utf8")
                    indent = node.start_point[1]
                    line_num = node.start_point[0]
                    structures.append((struct_type, name, indent, line_num))
            else:
                # Fallback or other language implementations would go here
                print(
                    f"Language '{language}' not supported for code structure analysis."
                )
                return None

            # Sort by line number
            structures.sort(key=lambda s: s[3])

            # Create visual representation
            width = min(options.width, 80)
            height = min(len(structures) * 2 + 2, options.height)

            if not structures:
                return AnsiArtDocument(width, height)

            doc = AnsiArtDocument(width, height, "#1e1e1e", "#ffffff")

            y = 1
            for struct_type, name, indent, _ in structures:
                if y >= height - 1:
                    break

                box_indent = indent // 2

                if struct_type == "class":
                    color = "#569cd6"  # Blue for classes
                    symbol = "◆"
                else:
                    color = "#dcdcaa"  # Yellow for functions
                    symbol = "○"

                # Draw symbol and name
                line_text = f"{' ' * box_indent}{symbol} {name}"
                for i, ch in enumerate(line_text):
                    if i < width:
                        doc.ch[y][i] = ch
                        doc.st[y][i] = Style(color=color, bgcolor="#1e1e1e")

                y += 2

            return doc

        except Exception as e:
            print(f"Error generating code structure art: {e}")
            return None


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Helper Functions
# ═══════════════════════════════════════════════════════════════════════════════


async def open_file_in_paint(app: Any, file_path: Path) -> bool:
    """Open a file in the Paint tool from another tool."""
    try:
        # Import paint screen
        from aura_cli.tui.screens.paint_screen import PaintScreen

        # Push paint screen with file
        screen = PaintScreen(file_path=file_path)
        app.push_screen(screen)
        return True
    except Exception as e:
        app.notify(f"Error opening in Paint: {e}", severity="error")
        return False


def get_ansi_preview(file_path: Path, max_width: int = 80, max_height: int = 24) -> str:
    """Get a preview string of an ANSI art file."""
    try:
        from aura_cli.application.paint.ansi_art_document import AnsiArtDocument

        doc = AnsiArtDocument(max_width, max_height)
        content = file_path.read_bytes()
        doc.decode_based_on_file_extension(content, str(file_path))

        # Convert to simple string
        lines = []
        for y in range(min(doc.height, max_height)):
            line = "".join(doc.ch[y][:max_width])
            lines.append(line)

        return "\n".join(lines)
    except Exception:
        return ""


def export_document_to_format(
    doc: AnsiArtDocument, output_path: Path, output_format: str = "ANSI"
) -> bool:
    """Export an AnsiArtDocument to a specific format."""
    try:
        content = doc.encode_to_format(output_format)

        if isinstance(content, bytes):
            output_path.write_bytes(content)
        else:
            output_path.write_text(content)

        return True
    except Exception:
        return False
