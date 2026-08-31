"""Gallery - Aura CLI Paint Tool

ANSI art gallery viewer with navigation and animations.

Features:
    - Folder and file browsing
    - Keyboard navigation (arrows, page up/down, home/end)
    - Smooth transition animations
    - Version filtering (shows latest vX.Y files)
    - Multiple format support (.ans, .txt)
    - Dark mode toggle
"""

import argparse
import locale
import os
from pathlib import Path
import re
from typing import ClassVar, Dict, List, Tuple

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, ScrollableContainer
from textual.reactive import Reactive, var
from textual.widgets import Footer, Header, Static

from aura_cli.application.paint.ansi_art_document import AnsiArtDocument

from .__init__ import __version__
from .auto_restart import restart_on_changes, restart_program

parser = argparse.ArgumentParser(
    description="ANSI art gallery",
    usage="%(prog)s [path]",
    prog="python -m src.textual_paint.gallery",
)
parser.add_argument(
    "path",
    nargs="?",
    default=None,
    help="Path to a folder containing ANSI art, or an ANSI file.",
)
parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
parser.add_argument(
    "--no-animation", action="store_true", help="Disable transition effects"
)

dev_options = parser.add_argument_group("development options")
dev_options.add_argument(
    "--inspect-layout",
    action="store_true",
    help="Enables DOM inspector (F12) and middle click highlight",
)
dev_options.add_argument(
    "--restart-on-changes",
    action="store_true",
    help="Restart the app when the source code is changed",
)

args = parser.parse_args(os.environ.get("PYTEST_GALLERY_ARGS", "").split() or None)


def _(text: str) -> str:
    """Return untranslated gallery text until this standalone view uses i18n."""
    return text


class GalleryItem(Container):
    """ANSI art image with caption.

    Displays an ANSI art document in a scrollable container
    with a caption below. Supports animated position transitions.

    Attributes:
        position: Horizontal offset multiplier for slide animations
        image: AnsiArtDocument to display
        caption: Text caption below image
    """

    position: Reactive[float] = var(0)

    def __init__(self, image: AnsiArtDocument, caption: str):
        """Initialize gallery item.

        Args:
            image: AnsiArtDocument to display
            caption: Caption text for the image
        """
        super().__init__()
        self.image = image
        self.caption = caption

    def compose(self) -> ComposeResult:
        """Compose gallery item layout.

        Yields:
            ScrollableContainer with image and caption Static widgets
        """
        text = self.image.get_renderable()
        text.no_wrap = True
        yield ScrollableContainer(
            Static(text, classes="image"), classes="image_container"
        )
        yield Static(self.caption, classes="caption")

    def watch_position(self, value: float) -> None:
        """Update horizontal offset when position changes.

        Args:
            value: Position multiplier (0=center, -1=left, 1=right)
        """
        self.styles.offset = (round(self.app.size.width * value), 0)


class GalleryApp(App[None]):
    """ANSI art gallery application.

    Textual app for browsing ANSI art files with keyboard navigation
    and smooth transitions between images.

    Attributes:
        path_index: Current image index in paths list
        paths: List of Path objects for all gallery images
        gallery_item_by_path: Cache of loaded GalleryItem widgets
    """

    TITLE = "ANSI art gallery"

    CSS_PATH = "gallery.css"

    BINDINGS: ClassVar[list] = [
        Binding("ctrl+q", "quit", _("Quit"), priority=True),
        Binding("ctrl+d", "toggle_dark", _("Toggle Dark Mode")),
        Binding("left,pageup", "previous", _("Previous"), priority=True),
        Binding("right,pagedown", "next", _("Next"), priority=True),
        Binding("home", "scroll_to_start", _("First"), priority=True, show=False),
        Binding("end", "scroll_to_end", _("Last"), priority=True, show=False),
        # dev helper
        # f5 would be more traditional, but I need something not bound to anything
        # in the context of the terminal in VS Code, and not used by this app, like Ctrl+R, and detectable in the terminal.
        # This isn't that important since I have automatic reloading,
        # but it still comes in handy sometimes.
        Binding("f2", "reload", _("Reload"), show=False),
        # Dev tool to inspect the widget tree.
        Binding("f12", "toggle_inspector", _("Toggle Inspector"), show=False),
    ]

    path_index: Reactive[int] = var(0)

    def __init__(self) -> None:
        """Initialize gallery app with empty state."""
        super().__init__()
        self.paths: List[Path] = []
        self.gallery_item_by_path: Dict[Path, GalleryItem] = {}

    def compose(self) -> ComposeResult:
        """Compose app layout.

        Yields:
            Header, Container, Footer, and optional Inspector widgets
        """
        yield Header()

        self.container = Container()
        yield self.container

        yield Footer()

        if not args.inspect_layout:
            return
        # importing the inspector adds instrumentation which can slow down startup
        from .inspector import Inspector

        inspector = Inspector()
        inspector.display = False
        yield inspector

    def on_mount(self) -> None:
        """Load gallery on mount."""
        self._load()

    def _load(self) -> None:
        """Load and filter ANSI art files from specified path.

        Loads files from command-line path or default samples folder.
        Filters by extension (.ans, .txt), sorts by version number,
        and optionally hides old versions.
        """
        hide_old_versions = False
        if args.path is None:
            gallery_folder = Path(os.path.dirname(__file__), "../../samples").resolve()
            hide_old_versions = True
        else:
            gallery_folder = Path(args.path)

        if not gallery_folder.exists():
            self.exit(None, message=Text(f"Folder or file not found: {gallery_folder}"))
            return

        file_to_show = None
        if gallery_folder.is_file():
            # allow showing a specific file, and load whatever folder it's in
            file_to_show = gallery_folder
            gallery_folder = gallery_folder.parent

        exts = (".ans", ".txt")

        paths = gallery_folder.rglob("**/*")
        paths = [path for path in paths if path.is_file() and path.suffix in exts]

        # First sort by whole path
        paths = sorted(paths, key=lambda path: locale.strxfrm(str(path)))
        # Then (higher priority) sort by version number (vX.Y) numerically where present
        # Actually, it might be simpler to handle any numbers in the filename, using Decorate-Sort-Undecorate.
        # Well, I can do it mostly, but for comparing "v1" and "v1.1", I need to consider the version number as a group.
        # For two-number version strings, I could consider it as a float, but for three-number version strings, a tuple should work.
        # I don't have any three-number version strings in the filenames of my ANSI art samples, but TODO: generalize this.
        matches_and_paths = [
            (re.findall(r"(\d*(?:\.\d+)?)(\D*)", str(path)), path) for path in paths
        ]
        sorted_parts_and_paths = sorted(
            matches_and_paths,
            key=lambda matches_and_path: [
                [
                    # If ints or strings are conditionally omitted, it leads to int vs str comparison errors.
                    # *([float(match[0])] if match[0] else []),
                    # *([locale.strxfrm(match[1])] if match[1] else []),
                    # So just keep it as an alternating list of floats and strings. Simpler, and safer.
                    float(match[0]) if match[0] else float("inf"),
                    locale.strxfrm(match[1]),
                ]
                for match in matches_and_path[0]
            ],
        )
        paths = [path for _, path in sorted_parts_and_paths]

        if hide_old_versions:
            # Hide any paths that are not the latest version of a file,
            # for files matching some_identifier_vX.Y_optional_comment.ext
            latest_versions: Dict[str, Tuple[float, Path]] = {}
            for path in paths:
                version_match = re.match(r"(.+)_v(\d+(?:\.\d+)?)", path.stem)
                if version_match:
                    file_id = version_match.group(1)
                    version = float(version_match.group(2))
                    if file_id in latest_versions:
                        if version > latest_versions[file_id][0]:
                            latest_versions[file_id] = version, path
                    else:
                        latest_versions[file_id] = version, path
                else:
                    latest_versions[str(path)] = -1, path
            paths = [path for _, path in latest_versions.values()]

            # Hide some uninteresting files
            paths = [
                path
                for path in paths
                if not re.match(
                    "0x0|1x1|2x2|4x4_font_template|gradient_test|pipe_strip_mega|cp437_as_utf8|galaxies_v1",
                    path.name,
                )
            ]

        exts_str = ", ".join(f"*{ext}" for ext in exts)
        if file_to_show:
            try:
                index_to_show = [*map(str, paths)].index(str(file_to_show))
            except ValueError:
                self.exit(
                    None,
                    message=Text(f"Not an ANSI art file ({exts_str}): {file_to_show}"),
                )
                return
        else:
            index_to_show = 0

        if len(paths) == 0:
            self.exit(
                None,
                message=Text(
                    f"No ANSI art ({exts_str}) found in folder: {gallery_folder}"
                ),
            )
            return

        self.paths = paths
        self.gallery_item_by_path = {}
        self.path_index = index_to_show
        self._load_upcoming_images()

    def _load_upcoming_images(self) -> None:
        """Load current image and 2 images before/after for smooth navigation."""
        range_start = max(self.path_index - 2, 0)
        range_end = min(self.path_index + 2, len(self.paths))

        for path in self.paths[range_start:range_end]:
            if path not in self.gallery_item_by_path:
                self._load_image(path)

    def _load_image(self, path: Path) -> None:
        """Load ANSI art file and create gallery item.

        Args:
            path: Path to ANSI art file to load
        """
        # with open(path, "r", encoding="cp437") as f:
        with open(path, encoding="utf8") as f:
            image = AnsiArtDocument.from_ansi(f.read())

        gallery_item = GalleryItem(image, caption=path.name)
        self.container.mount(gallery_item)
        item_index = self.paths.index(path)
        # gallery_item.styles.opacity = 1.0 if item_index == self.path_index else 0.0
        gallery_item.position = (
            0
            if item_index == self.path_index
            else (-1 if item_index < self.path_index else 1)
        )
        self.gallery_item_by_path[path] = gallery_item

    def validate_path_index(self, path_index: int) -> int:
        """Clamp path index to valid range.

        Args:
            path_index: Requested index

        Returns:
            Index clamped to [0, len(paths)-1]
        """
        return max(0, min(path_index, len(self.paths) - 1))

    def watch_path_index(self, current_index: int) -> None:
        """Update gallery when path index changes.

        Args:
            current_index: New current image index

        Note:
            Loads upcoming images and animates position transitions.
        """
        self._load_upcoming_images()
        for path, gallery_item in self.gallery_item_by_path.items():
            item_index = self.paths.index(path)
            # opacity = 1.0 if item_index == current_index else 0.0
            # gallery_item.styles.animate("opacity", value=opacity, final_value=opacity, duration=0.5)
            position = (
                0
                if item_index == current_index
                else (-1 if item_index < current_index else 1)
            )
            if args.no_animation:
                gallery_item.position = position
            else:
                gallery_item.animate(
                    "position", value=position, final_value=position, duration=0.3
                )

        self.sub_title = f"{current_index + 1}/{len(self.paths)}"

    def action_next(self) -> None:
        """Navigate to next image."""
        self.path_index += 1

    def action_previous(self) -> None:
        """Navigate to previous image."""
        self.path_index -= 1

    def action_scroll_to_start(self) -> None:
        """Jump to first image."""
        self.path_index = 0

    def action_scroll_to_end(self) -> None:
        """Jump to last image."""
        self.path_index = len(self.paths) - 1

    def action_reload(self) -> None:
        """Restart the application."""
        restart_program()

    def action_toggle_inspector(self) -> None:
        """Toggle DOM inspector visibility."""
        if not args.inspect_layout:
            return
        # importing the inspector adds instrumentation which can slow down startup
        from .inspector import Inspector

        inspector = self.query_one(Inspector)
        inspector.display = not inspector.display
        if not inspector.display:
            inspector.picking = False


app = GalleryApp()

if args.restart_on_changes:
    restart_on_changes(app)

if __name__ == "__main__":
    app.run()
