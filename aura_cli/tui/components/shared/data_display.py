"""
Shared Data Display Components.

Provides key-value tables, tree views, and other data visualization widgets.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from textual import on
from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Tree


@dataclass
class TreeNode:
    """A node in a tree view."""

    id: str
    label: str
    icon: str = ""
    children: List[TreeNode] = field(default_factory=list)
    data: Any = None
    expanded: bool = False


class KeyValueTable(Widget):
    """
    Table for displaying key-value pairs.

    Example:
        ```python
        table = KeyValueTable(data={
            "Name": "main.py",
            "Size": "1.2 KB",
            "Modified": "2024-01-15",
        })
        ```
    """

    def __init__(
        self,
        data: Optional[Dict[str, Any]] = None,
        key_header: str = "Property",
        value_header: str = "Value",
        show_header: bool = True,
        **kwargs,
    ):
        """Initialize the instance."""
        super().__init__(**kwargs)
        self._data = data or {}
        self._key_header = key_header
        self._value_header = value_header
        self._show_header = show_header

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        table = DataTable(show_header=self._show_header, id="kv-table")  # type: ignore[var-annotated]
        yield table

    def on_mount(self) -> None:
        """Populate table on mount."""
        self._populate_table()

    def _populate_table(self) -> None:
        """Populate the table with data."""
        try:
            table = self.query_one("#kv-table", DataTable)
            table.clear(columns=True)

            table.add_column(self._key_header, key="key")
            table.add_column(self._value_header, key="value")

            for key, value in self._data.items():
                table.add_row(str(key), str(value))
        except Exception as error:
            self.log.debug("Key-value table is not mounted yet: %s", error)

    def update_data(self, data: Dict[str, Any]) -> None:
        """Update the table data."""
        self._data = data
        self._populate_table()

    def set_value(self, key: str, value: Any) -> None:
        """Set a single value."""
        self._data[key] = value
        self._populate_table()

    def get_value(self, key: str) -> Optional[Any]:
        """Get a value by key."""
        return self._data.get(key)


class TreeView(Widget):
    """
    Hierarchical tree view widget.

    Example:
        ```python
        root = TreeNode("root", "Project", icon="▷", children=[
            TreeNode("src", "src", icon="▷", children=[
                TreeNode("main", "main.py", icon="◇"),
            ]),
            TreeNode("tests", "tests", icon="▷"),
        ])
        tree = TreeView(root=root)
        ```
    """

    class NodeSelected(Message):
        """Message when a node is selected."""

        def __init__(self, node: TreeNode) -> None:
            """Initialize the widget."""
            super().__init__()
            self.node = node

    class NodeExpanded(Message):
        """Message when a node is expanded."""

        def __init__(self, node: TreeNode) -> None:
            """Initialize the widget."""
            super().__init__()
            self.node = node

    class NodeCollapsed(Message):
        """Message when a node is collapsed."""

        def __init__(self, node: TreeNode) -> None:
            """Initialize the widget."""
            super().__init__()
            self.node = node

    def __init__(self, root: Optional[TreeNode] = None, label: str = "Tree", **kwargs):
        """Initialize the widget."""
        super().__init__(**kwargs)
        self._root = root
        self._label = label
        self._node_map: Dict[str, TreeNode] = {}

    def compose(self) -> ComposeResult:
        """Compose the widget layout."""
        tree = Tree(self._label, id="tree")  # type: ignore[var-annotated]
        yield tree

    def on_mount(self) -> None:
        """Build tree on mount."""
        if self._root:
            self._build_tree()

    def _build_tree(self) -> None:
        """Build the tree structure."""
        try:
            tree = self.query_one("#tree", Tree)
            tree.clear()

            self._node_map.clear()
            self._add_node(tree.root, self._root)  # type: ignore[arg-type]
        except Exception as error:
            self.log.debug("Tree display is not mounted yet: %s", error)

    def _add_node(self, parent, node: TreeNode) -> None:
        """Add a node to the tree."""
        icon_part = f"{node.icon} " if node.icon else ""
        label = f"{icon_part}{node.label}"

        self._node_map[node.id] = node

        if node.children:
            tree_node = parent.add(label, data=node.id, expand=node.expanded)
            for child in node.children:
                self._add_node(tree_node, child)
        else:
            parent.add_leaf(label, data=node.id)

    def set_root(self, root: TreeNode) -> None:
        """Set the root node."""
        self._root = root
        self._build_tree()

    def get_node(self, node_id: str) -> Optional[TreeNode]:
        """Get a node by ID."""
        return self._node_map.get(node_id)

    def refresh_tree(self) -> None:
        """Refresh the tree display."""
        self._build_tree()

    @on(Tree.NodeSelected)
    def on_tree_node_selected(self, event: Tree.NodeSelected) -> None:
        """Handle tree node selection."""
        node_id = event.node.data
        if node_id:
            node = self._node_map.get(node_id)
            if node:
                self.post_message(self.NodeSelected(node))

    @on(Tree.NodeExpanded)
    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle tree node expansion."""
        node_id = event.node.data
        if node_id:
            node = self._node_map.get(node_id)
            if node:
                node.expanded = True
                self.post_message(self.NodeExpanded(node))

    @on(Tree.NodeCollapsed)
    def on_tree_node_collapsed(self, event: Tree.NodeCollapsed) -> None:
        """Handle tree node collapse."""
        node_id = event.node.data
        if node_id:
            node = self._node_map.get(node_id)
            if node:
                node.expanded = False
                self.post_message(self.NodeCollapsed(node))
