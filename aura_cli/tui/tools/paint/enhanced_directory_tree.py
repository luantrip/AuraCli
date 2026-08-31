"""Enhanced Directory Tree - Aura CLI Paint Tool

Extended DirectoryTree widget with advanced navigation features.

Features:
    - Auto-expansion to target paths
    - Hidden file filtering (.files, ~backups)
    - ASCII-only icon mode support
    - Programmatic node selection and scrolling
    - Cross-platform path handling
"""

from pathlib import Path
from typing import Callable, Iterable, Tuple

from rich.style import Style
from rich.text import Text, TextType
from textual.reactive import var
from textual.widgets import DirectoryTree, Tree
from textual.widgets._directory_tree import DirEntry
from textual.widgets._tree import TOGGLE_STYLE, TreeNode

# from paint.args import args
from .__init__ import PYTEST
from .ascii_mode import replace

# Vague skeuomorphism

# Simple generic tree style + new way of handling --ascii-only mode
FILE_ICON = Text("📄 ")
FOLDER_OPEN_ICON = Text("📂 ")
FOLDER_CLOSED_ICON = Text("📁 ")
icons = locals()
replace(icons, "FILE_ICON", Text.from_markup(""))
replace(icons, "FOLDER_OPEN_ICON", Text.from_markup("[blue]-[/] "))
replace(icons, "FOLDER_CLOSED_ICON", Text.from_markup("[blue]+[/] "))


class EnhancedDirectoryTree(DirectoryTree):
    """DirectoryTree with auto-expansion and filtering.

    Extends Textual's DirectoryTree with programmatic navigation,
    hidden file filtering, and ASCII icon support.

    Attributes:
        node_highlighted_by_expand_to_path: Flag indicating if NodeHighlighted
            was triggered by expand_to_path method
    """

    node_highlighted_by_expand_to_path = var(False)

    def filter_paths(self, paths: Iterable[Path]) -> Iterable[Path]:
        """Filter out hidden and backup files.

        Args:
            paths: Iterable of Path objects to filter

        Returns:
            Filtered paths excluding .hidden, ~backup, and ~prefix files
        """
        return [
            path
            for path in paths
            if not (
                path.name.startswith(".")
                or path.name.endswith("~")
                or path.name.startswith("~")
            )
        ]

    def _go_to_node(
        self, node: TreeNode[DirEntry], callback: Callable[[], None]
    ) -> None:
        """Scroll to node and select it.

        Args:
            node: Tree node to navigate to
            callback: Function to call after navigation completes
        """

        def _go_to_node_now():
            self.node_highlighted_by_expand_to_path = True
            self.select_node(node)
            # So instead, listen for NodeHighlighted, and then clear the flag.

            region = self._get_label_region(node._line)  # pyright: ignore[reportPrivateUsage]
            assert region, "Node not found in tree"
            self.scroll_to_region(region, animate=False, top=True)

            callback()

        # Is there a way to avoid this delay?
        self.set_timer(0.01, _go_to_node_now)

    def on_tree_node_highlighted(self, event: Tree.NodeHighlighted[DirEntry]) -> None:
        """Handle node highlight event and clear expand_to_path flag.

        Args:
            event: NodeHighlighted event from tree widget

        Note:
            Clears flag after event bubbling completes to prevent
            interference with parent widget handlers.
        """

        def clear_flag() -> None:
            self.node_highlighted_by_expand_to_path = False

        self.call_after_refresh(clear_flag)

    def _expand_matching_child(
        self,
        node: TreeNode[DirEntry],
        remaining_parts: Tuple[str, ...],
        callback: Callable[[], None],
    ) -> None:
        """Recursively expand child nodes matching path parts.

        Args:
            node: Current tree node to expand from
            remaining_parts: Tuple of remaining path parts to match
            callback: Function to call when final node is reached

        Note:
            Hooks into DirectoryTree's add method to handle dynamically
            loaded nodes during expansion.
        """
        if not remaining_parts:
            # I noticed this happening when testing with pyfakefs.
            # os.cwd() is faked to return "/" by default, leading to this edge case
            # where the EnhancedDirectoryTree is "expanded" to the root.
            return
        orig_add = node.add
        _expand_matching_child = self._expand_matching_child
        _add_to_load_queue = self._add_to_load_queue
        _go_to_node = self._go_to_node

        def expand_if_match(node: TreeNode[DirEntry]) -> None:
            if node.data and node.data.path.parts[-1] == remaining_parts[0]:
                if len(remaining_parts) > 1:
                    if node.data.path.is_dir():
                        sliced_parts = remaining_parts[1:]
                        _expand_matching_child(node, sliced_parts, callback)
                        _add_to_load_queue(node)
                else:
                    _go_to_node(node, callback)
                    # If the target path is a directory, expand it.
                    # This might not always be desired, for a general API,
                    # but for File > New, File > Open, it should expand the current directory.
                    if node.data.path.is_dir():
                        _add_to_load_queue(node)

        def add(
            self: TreeNode[DirEntry],
            label: TextType,
            data: DirEntry | None = None,
            *,
            expand: bool = False,
            allow_expand: bool = True,
        ) -> TreeNode[DirEntry]:
            node = orig_add(label, data, expand=expand, allow_expand=allow_expand)
            expand_if_match(node)
            # Note: The hook is left indefinitely.
            # It may be worth some consideration as to whether this could pose any problems.
            # However, we can't just reset to orig_add here since that would make this only handle the first added node.
            return node

        # Hook the add method to handle new nodes.
        node.add = add.__get__(node, type(node))
        # Also expand children of the node already loaded.
        for child in node.children:
            expand_if_match(child)

    def expand_to_path(
        self, target_path: str | Path, callback: Callable[[], None] | None = None
    ) -> None:
        """Expand directory tree to target path, loading directories as needed.

        Args:
            target_path: Path to expand to (string or Path object)
            callback: Optional function to call after expansion completes

        Note:
            Automatically loads intermediate directories and scrolls to
            final node. Expands target directory if it's a folder.
        """

        target_path = Path(target_path)

        if callback is None:

            def callback() -> None:
                pass

        self._expand_matching_child(self.root, target_path.parts[1:], callback)

    def render_label(
        self, node: TreeNode[DirEntry], base_style: Style, style: Style
    ) -> Text:
        """Render node label with dynamic icons for ASCII-only mode.

        Args:
            node: Tree node to render
            base_style: Base widget style
            style: Additional label style

        Returns:
            Rich Text object with icon prefix and styled label
        """
        node_label = node._label.copy()  # pyright: ignore[reportPrivateUsage]

        if PYTEST and node_label.plain == "\\":
            # Normalize root node display for cross-platform snapshot testing.
            # (Setting pyfakefs's fs.os = OSType.LINUX caused bigger problems.)
            node_label.plain = "/"

        node_label.stylize(style)

        if node._allow_expand:  # pyright: ignore[reportPrivateUsage]
            prefix = (
                FOLDER_OPEN_ICON if node.is_expanded else FOLDER_CLOSED_ICON
            ).copy()
            prefix.stylize_before(base_style + TOGGLE_STYLE)
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--folder", partial=True)
            )
        else:
            prefix = FILE_ICON.copy()
            prefix.stylize_before(base_style)
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--file", partial=True),
            )
            node_label.highlight_regex(
                r"\..+$",
                self.get_component_rich_style(
                    "directory-tree--extension", partial=True
                ),
            )

        if node_label.plain.startswith("."):
            node_label.stylize_before(
                self.get_component_rich_style("directory-tree--hidden")
            )

        return prefix + node_label
