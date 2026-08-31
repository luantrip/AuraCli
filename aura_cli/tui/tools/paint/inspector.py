"""Inspector - Aura CLI Paint Tool

DOM inspector development tool for Textual applications.

Features:
    - Widget tree visualization with hierarchy
    - CSS styles inspection (computed, inline, user)
    - Live style editing with validation
    - Source code navigation for inline styles
    - Widget picking with middle-click
    - Property inspection and modification
    - Call stack tracking for style changes
    - Syntax highlighting for values

Author: Isaiah Odhner
License: MIT
"""

import asyncio
import inspect
import logging
import os
from typing import (
    Any,
    ClassVar,
    Dict,
    Iterable,
    List,
    Literal,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
    TypeGuard,
)

from rich.highlighter import ReprHighlighter
from rich.markup import escape
from rich.segment import Segment
from rich.style import Style
from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.color import Color, ColorParseError
from textual.containers import Container, VerticalScroll
from textual.css.errors import DeclarationError
from textual.css.model import RuleSet
from textual.css.parse import parse_declarations
from textual.css.styles import RulesMap, Styles, StylesBase
from textual.css.tokenizer import TokenError
from textual.dom import DOMNode
from textual.errors import NoWidget
from textual.geometry import Offset, Region, Size
from textual.message import Message
from textual.reactive import reactive, var
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import (
    Button,
    DataTable,
    Input,
    Static,
    TabbedContent,
    TabPane,
    Tree,
)
from textual.widgets.tree import TreeNode

from .inspector_model import safe_object_items, subtract_regions
from .launch_editor import launch_editor

logger = logging.getLogger(__name__)

# from textual.css._style_properties import BorderDefinition


# Instrument style setting in order to link to the source code where inline styles are set.
# Set to False to disable call-stack tracking for better performance.
TRACK_INLINE_STYLE_CALL_STACKS: bool = True

inline_style_call_stacks: Dict[DOMNode, Dict[str, List[inspect.FrameInfo]]] = {}

original_set_rule = Styles.set_rule


def set_rule(self: Styles, rule: str, value: object | None) -> bool:
    if TRACK_INLINE_STYLE_CALL_STACKS and self.node and self.node.styles.inline is self:
        if self.node not in inline_style_call_stacks:
            inline_style_call_stacks[self.node] = {}
        inline_style_call_stacks[self.node][rule] = inspect.stack()
    return original_set_rule.__get__(self)(rule, value)


Styles.set_rule = set_rule

original_merge = Styles.merge


def merge(self: Styles, other: StylesBase) -> None:
    if self.node and self.node.styles.inline is self:
        if self.node not in inline_style_call_stacks:
            inline_style_call_stacks[self.node] = {}
        stack = inspect.stack()
        for rule in other.get_rules():
            inline_style_call_stacks[self.node][rule] = stack
    return original_merge.__get__(self)(other)


Styles.merge = merge

original_merge_rules = Styles.merge_rules


def merge_rules(self: Styles, rules: RulesMap) -> None:
    if self.node and self.node.styles.inline is self:
        if self.node not in inline_style_call_stacks:
            inline_style_call_stacks[self.node] = {}
        stack = inspect.stack()
        for rule in rules:
            inline_style_call_stacks[self.node][rule] = stack
    return original_merge_rules.__get__(self)(rules)


Styles.merge_rules = merge_rules

rule_set_call_stacks: Dict[RuleSet, List[inspect.FrameInfo]] = {}
original_rule_set_init = RuleSet.__init__


def rule_set_init(self: RuleSet, *args: Any, **kwargs: Any):
    original_rule_set_init.__get__(self)(*args, **kwargs)
    rule_set_call_stacks[self] = inspect.stack()


RuleSet.__init__ = rule_set_init


class DOMTree(Tree[DOMNode]):
    """A widget that displays the widget hierarchy."""

    def on_mount(self) -> None:
        """Start periodic live updates of the DOM tree."""
        self.set_interval(2.0, self._live_update)

    def _live_update(self) -> None:
        """Refresh visible tree nodes to reflect DOM changes."""
        if self.root.is_expanded:
            for node in self.root.children:
                dom_node = node.data
                if dom_node is not None:
                    node.set_label(dom_node.css_identifier_styled)
                    node.allow_expand = len(dom_node.children) > 0

    class Hovered(Message, bubble=True):
        """Posted when a node in the tree is hovered with the mouse or highlighted with the keyboard.

        Handled by defining a `on_domtree_hovered` method on a parent widget.
        """

        def __init__(
            self,
            tree: "DOMTree",
            tree_node: TreeNode[DOMNode] | None,
            dom_node: DOMNode | None,
        ) -> None:
            """Initialise the Hovered message.

            Args:
                tree: The `DOMTree` that had a node hovered.
                tree_node: The tree node for the file that was hovered.
                dom_node: The DOM node that was hovered.
            """
            super().__init__()
            self.tree: DOMTree = tree
            """The `DOMTree` that had a node hovered."""
            self.tree_node: TreeNode[DOMNode] | None = tree_node
            """The tree node that was hovered. Only _represents_ the DOM node."""
            self.dom_node: DOMNode | None = dom_node
            """The DOM node that was hovered."""

        # @property
        # def control(self) -> "DOMTree":
        #     """The `DOMTree` that had a node hovered.

        #     This is an alias for [`Hovered.tree`][textual_paint.inspector.DOMTree.Hovered.tree]
        #     which is used by the [`on`][textual.on] decorator.
        #     """
        #     return self.tree

    class Selected(Message, bubble=True):
        """Posted when a node in the tree is selected.

        Handled by defining a `on_domtree_selected` method on a parent widget.
        """

        def __init__(
            self, tree: "DOMTree", tree_node: TreeNode[DOMNode], dom_node: DOMNode
        ) -> None:
            """Initialise the Selected message.

            Args:
                tree: The `DOMTree` that had a node selected.
                tree_node: The tree node for the file that was selected.
                dom_node: The DOM node that was selected.
            """
            super().__init__()
            self.tree: DOMTree = tree
            """The `DOMTree` that had a node selected."""
            self.tree_node: TreeNode[DOMNode] = tree_node
            """The tree node that was selected. Only _represents_ the DOM node."""
            self.dom_node: DOMNode = dom_node
            """The DOM node that was selected."""

    def __init__(
        self,
        root: DOMNode,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        """Initialise the DOMTree widget."""
        super().__init__(
            root.css_identifier_styled,
            root,
            name=name,
            id=widget_id,
            classes=classes,
            disabled=disabled,
        )

    def _on_tree_node_expanded(self, event: Tree.NodeExpanded[DOMNode]) -> None:
        """Called when a node is expanded; loads the children."""
        event.stop()
        dom_node = event.node.data
        if dom_node is None:
            return
        # event.node.remove_children() was inefficient and maybe caused some other problems
        for child in dom_node.children:
            exists = False
            for node in event.node.children:
                if node.data == child:
                    exists = True
                    break
            if exists:
                continue
            event.node.add(
                child.css_identifier_styled,
                data=child,
                allow_expand=len(child.children) > 0,
            )

    def _on_tree_node_highlighted(self, event: Tree.NodeHighlighted[DOMNode]) -> None:
        """Called when a node is highlighted with the keyboard."""
        event.stop()
        dom_node = event.node.data
        if dom_node is None:
            return
        self.post_message(self.Hovered(self, event.node, dom_node))

    def _on_tree_node_selected(self, event: Tree.NodeSelected[DOMNode]) -> None:
        """Called when a node is selected with the mouse or keyboard."""
        event.stop()
        dom_node = event.node.data
        if dom_node is None:
            return
        self.post_message(self.Selected(self, event.node, dom_node))

    def watch_hover_line(self, previous_hover_line: int, hover_line: int) -> None:
        """Extend the hover line watcher to post a message when a node is hovered."""
        # Could use self.watch() instead https://textual.textualize.io/api/dom_node/#textual.dom.DOMNode.watch
        super().watch_hover_line(previous_hover_line, hover_line)
        node: TreeNode[DOMNode] | None = (
            self._get_node(hover_line) if hover_line > -1 else None
        )
        if node is not None:
            assert isinstance(node.data, DOMNode), (
                "All nodes in DOMTree should have DOMNode data, got: " + repr(node.data)
            )
            self.post_message(self.Hovered(self, node, node.data))
        else:
            self.post_message(self.Hovered(self, None, None))

    def on_leave(self, event: events.Leave) -> None:
        """Handle the mouse leaving the tree."""
        self.hover_line = -1

    async def expand_to_dom_node(self, dom_node: DOMNode) -> None:
        """Drill down to the given DOM node in the tree."""
        tree_node = self.root
        ancestors = list(reversed(dom_node.ancestors_with_self))
        for ancestor_node in ancestors:
            for node in (
                *tree_node.children,
                tree_node,
            ):  # tree_node in case it's the root
                if node.data == ancestor_node:
                    tree_node = node
                    tree_node.expand()

                    async def wait_for_expand() -> None:
                        # while not tree_node.is_expanded: # this is set immediately
                        #     await asyncio.sleep(0.01)
                        await asyncio.sleep(0.01)

                    task = asyncio.create_task(wait_for_expand())
                    self._wait_for_expand = task
                    await task
                    del self._wait_for_expand
                    break
        self.select_node(tree_node)
        self.scroll_to_node(tree_node)
        auto_expand = self.auto_expand
        self.auto_expand = False
        self.action_select_cursor()
        self.auto_expand = auto_expand


class _ShowMoreSentinelType:
    pass


_ShowMoreSentinel = _ShowMoreSentinelType()
"""A sentinel that represents an ellipsis that can be clicked to load more properties."""
del _ShowMoreSentinelType


class PropertiesTree(Tree[object]):
    """A widget for exploring the attributes/properties of an object."""

    highlighter = ReprHighlighter()
    show_private: reactive[bool] = reactive(False)

    def __init__(
        self,
        label: str,
        root: object = None,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ):
        """Initialise the PropertiesTree widget."""
        super().__init__(
            label,
            root,
            name=name,
            id=widget_id,
            classes=classes,
            disabled=disabled,
        )

        self._already_loaded: Dict[TreeNode[object], Set[str]] = {}
        """A mapping of tree nodes to the keys that have already been loaded.

        This allows the tree to be collapsed and expanded without duplicating nodes.
        It's also used for lazy-loading nodes when clicking the ellipsis in long lists...
        """

        self._num_keys_accessed: Dict[TreeNode[object], int] = {}
        """A mapping of tree nodes to the number of keys that have been accessed."""

    def _on_tree_node_expanded(self, event: Tree.NodeExpanded[object]) -> None:
        """Called when a node is expanded; loads the children."""
        event.stop()
        self._populate_node(event.node)

    def _on_tree_node_selected(self, event: Tree.NodeSelected[object]) -> None:
        """Called when a node is selected with the mouse or keyboard."""
        event.stop()
        if event.node.data is _ShowMoreSentinel:
            event.node.remove()
            assert event.node.parent is not None, "Show more node should have a parent"
            self._populate_node(event.node.parent, load_more=True)

    @property
    def AAA_deal_with_it(self) -> Dict[str, Any]:
        """This property gives a grab bag of different types to test the tree."""
        from enum import Enum
        import traceback
        from typing import NamedTuple

        return {
            "a_string": "DEAL WITH IT 😎",
            "an_int": 42,
            "a_float": 3.14,
            "a_bool": True,
            "none": None,
            "a_list": ["a", "b", "c"],
            "a_tuple": ("a", "b", "c"),
            "a_named_tuple": NamedTuple(
                "a_named_tuple", [("a", int), ("b", str), ("c", float)]
            )(1, "2", 3.0),
            "a_set": {"a", "b", "c"},
            "a_frozenset": frozenset({"a", "b", "c"}),
            "a_dict": {"a": "A", "b": "B", "c": "C"},
            "a_dict_with_mixed_keys": {
                1: "A",
                "b": "B",
                Enum("an_enum", "a b c"): "C",
                frozenset(): "D",
            },
            "a_parameterized_generic": Dict[str, int],
            "a_module": inspect,
            "a_function": lambda x: x,  # type: ignore
            "a_generator": (x for x in "abc"),
            "an_iterator": iter("abc"),
            "a_range": range(10),
            "a_slice": slice(1, 2, 3),
            "a_complex": 1 + 2j,
            "a_bytes": b"abc",
            "a_bytearray": bytearray(b"abc"),
            "an_enum": Enum("an_enum", "a b c"),
            "an_ellipsis": ...,
            "a_memoryview": memoryview(b"abc"),
            "not_implemented": NotImplemented,
            "an_exception": Exception("hello"),
            "a_type": type,
            "a_code": compile("print('hello')", "<string>", "exec"),
            "a_frame": inspect.currentframe(),
            "a_traceback": traceback.extract_stack(),
        }

    @property
    def AAA_test_property_that_raises_exception(self) -> str:
        """This property raises an exception when accessed.

        Navigate to this node in the DOM Tree and look in the Properties Panel to see the error message.
        """
        raise Exception("EMIT: Error Message Itself Test")

    def filter_property(self, key: str, value: object) -> bool:
        """Return True if the property should be shown in the tree."""
        if not self.show_private and key.startswith("_"):
            return False
        return not callable(value)

    def toggle_private(self) -> None:
        """Toggle visibility of private (underscore-prefixed) properties."""
        self.show_private = not self.show_private
        self.root.collapse()
        self.root.expand()

    def _populate_node(self, node: TreeNode[object], load_more: bool = False) -> None:
        """Populate a node with its children, or some of them."""
        data: object = node.data
        if data is None:
            return

        if node not in self._already_loaded:
            self._already_loaded[node] = set()
            self._num_keys_accessed[node] = 0

        max_keys = 100
        if load_more:
            max_keys += self._num_keys_accessed[node]

        count = 0
        ellipsis_node: TreeNode[object] | None = None
        only_counting = False

        def with_no_error(key_val: Tuple[str, object]) -> Tuple[str, object, None]:
            return (key_val[0], key_val[1], None)

        if isinstance(data, dict):
            iterator: Iterable[Tuple[str, object, Exception | None]] = map(
                with_no_error, data.items()
            )  # type: ignore
        elif isinstance(data, Iterable) and not hasattr(data, "_fields"):  # type: ignore
            iterator = map(with_no_error, enumerate(data))  # type: ignore
        else:
            iterator = safe_object_items(data)  # type: ignore

        self._num_keys_accessed[node] = 0
        for key, value, exception in iterator:
            count += 1
            if only_counting:
                continue
            self._num_keys_accessed[node] += 1
            if not self.filter_property(str(key), value):
                continue
            if str(key) in self._already_loaded[node]:
                continue
            if count > max_keys:
                for child in node.children:
                    if child.data is _ShowMoreSentinel:
                        child.remove()
                ellipsis_node = node.add("...", _ShowMoreSentinel)
                ellipsis_node.allow_expand = False
                # break
                only_counting = True
                continue
            PropertiesTree._add_property_node(node, str(key), value, exception)
            self._already_loaded[node].add(str(key))
        if ellipsis_node is not None:
            ellipsis_node.label = f"... +{count - max_keys} more"

    @classmethod
    def _add_property_node(
        cls,
        parent_node: TreeNode[object],
        name: str,
        data: object,
        exception: Exception | None = None,
    ) -> None:
        """Adds data to a node.

        Based on https://github.com/Textualize/textual/blob/65b0c34f2ed6a69795946a0735a51a463602545c/examples/json_tree.py

        Args:
            parent_node (TreeNode): A Tree node to add a child to.
            name (str): The key that the data is associated with.
            data (object): Any object ideally should work.
        """

        node = parent_node.add(name, data)

        def with_name(text: Text) -> Text:
            """Formats a key=value line."""
            return Text.assemble(Text.styled(name, "bold"), "=", text)

        if exception is not None:
            node.allow_expand = False
            node.set_label(
                with_name(
                    Text.from_markup(
                        f"[i][#808080](getter error: [red]{escape(repr(exception))}[/red])[/#808080][/i]"
                    )
                )
            )
        elif isinstance(data, (list, set, frozenset, tuple)):
            length = len(data)  # type: ignore
            # node.set_label(Text(f"{name} ({length})"))
            # node.set_label(with_name(PropertiesTree.highlighter(repr(data))))
            # node.set_label(Text.assemble(
            #     Text.from_markup(f"[#808080]({length})[/#808080] "),
            #     with_name(PropertiesTree.highlighter(repr(data))),
            # ))
            # node.set_label(Text.assemble(
            #     with_name(PropertiesTree.highlighter(repr(data))),
            #     Text.from_markup(f" [#808080]({length})[/#808080]"),
            # ))
            # In the middle I think is best, although it's a little more complex:
            node.set_label(
                Text.assemble(
                    Text.styled(name, "bold"),
                    Text.styled(f"({length})", "#808080"),
                    "=",
                    PropertiesTree.highlighter(repr(data)),  # type: ignore
                )
            )
            # Can I perhaps DRY with with_name() with with_name taking a length parameter? In other words:
            # Can I maybe DRY this with with_name with with_name with with_name(text, length) as the signature?
        elif isinstance(data, (str, bytes, int, float, bool, type(None))):
            node.allow_expand = False
            node.set_label(with_name(PropertiesTree.highlighter(repr(data))))
        elif callable(data):
            # If the callable also has sub-attributes (e.g. widget.log which has .debug, .info etc.)
            # allow expanding it so those methods are accessible.
            has_sub_attrs = hasattr(data, "__dict__") and len(vars(data)) > 0
            node.allow_expand = has_sub_attrs
            node.set_label(
                Text.assemble(
                    f"{type(data).__name__} ",
                    Text.styled(name, "bold"),
                    PropertiesTree.highlighter(str(inspect.signature(data))),
                )
            )
        elif (
            hasattr(data, "__dict__")
            or hasattr(data, "__slots__")
            or isinstance(data, dict)
        ):
            # Pyright gives an error here due to the more specific "object | Dict[Unknown, Unknown]"
            # even though object is a superclass of dict and repr takes an object.
            node.set_label(with_name(PropertiesTree.highlighter(repr(data))))  # type: ignore
        else:
            node.allow_expand = False
            node.set_label(with_name(PropertiesTree.highlighter(repr(data))))


class NodeInfo(Container):
    DEFAULT_CSS = """
    NodeInfo {
        layers: style_value_input;
        max-height: 100vh;
    }
    .style_value_input,
    .style_value_error {
        layer: style_value_input;
        dock: top;
    }
    .style_value_input {
        border: none !important;
        padding: 0 !important;
    }
    .style_value_error {
        width: 1fr;
        color: red;
    }
    NodeInfo DataTable {
        height: 1fr;
    }
    """

    class FollowLinkToNode(Message):
        """A message sent when a link is clicked, pointing to a DOM node."""

        def __init__(self, dom_node: DOMNode) -> None:
            super().__init__()
            self.dom_node = dom_node

    class StaticWithLinkSupport(Static):
        """Static text that supports DOM node links and file opening links.

        This class exists because actions can't target an arbitrary parent.
        The only supported namespaces are `screen` and `app`.
        So action_select_node has to be defined directly on the widget that
        contains the @click actions.
        (Maybe it could be an ad-hoc method on the widget instead.)
        https://textual.textualize.io/guide/actions/#namespaces
        """

        def __init__(
            self,
            node_info: "NodeInfo",
            *,
            name: str | None = None,
            widget_id: str | None = None,
            classes: str | None = None,
            disabled: bool = False,
        ) -> None:
            super().__init__(
                name=name, id=widget_id, classes=classes, disabled=disabled
            )
            self._node_info = node_info

        def action_select_node(self, link_id: int) -> None:
            """Select a DOM node."""
            dom_node = self._node_info._link_id_to_node.get(link_id)
            if dom_node is None:
                return
            self.post_message(NodeInfo.FollowLinkToNode(dom_node))

        def action_open_file(
            self,
            path: str,
            line_number: int | None = None,
            column_number: int | None = None,
        ) -> None:
            """Open a file."""
            launch_editor(path, line_number, column_number)

    dom_node: var[DOMNode | None] = var[Optional[DOMNode]](None)
    """The DOM node being inspected."""

    def __init__(
        self,
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=widget_id, classes=classes, disabled=disabled)

        self._link_id_counter = 0
        """A counter used to generate unique IDs for links,
        since CSS selectors aren't unique (without something like `nth-child()`),
        and DOMNodes can't be used as arguments to an action function.
        """

        self._link_id_to_node: Dict[int, DOMNode] = {}
        """A mapping of link IDs to DOM nodes."""

        self._style_value_input = Input(classes="style_value_input")
        """An input for editing the value of a CSS style."""

        self._style_value_error = Static(classes="style_value_error")
        """An error message shown when the CSS value input is invalid."""

        self._editing_rule: str | None = None
        """The property name of the CSS declaration currently being edited."""

    def compose(self) -> ComposeResult:
        """Add sub-widgets."""
        # Previously NodeInfo could grow offscreen when resized, breaking the scrollbar.
        # Fixed by clamping height in ResizeHandle.on_mouse_move and adding max-height to NodeInfo CSS.
        yield ResizeHandle(self, "top")
        with TabbedContent(initial="properties"):
            with TabPane("Props", id="properties"):
                yield PropertiesTree("", classes="properties")
                yield Static(
                    "", classes="properties_nothing_selected tab_content_static"
                )
            with TabPane("CSS", id="styles"):
                yield VerticalScroll(
                    self.StaticWithLinkSupport(
                        self, classes="styles tab_content_static"
                    )
                )
            with TabPane("Keys", id="key_bindings"):
                # DataTable is placed after Static to avoid pushing Static down
                # when DataTable has display=False (Textual layout quirk).
                yield Static(
                    "", classes="key_bindings_nothing_selected tab_content_static"
                )
                yield VerticalScroll(DataTable[Text | str](classes="key_bindings"))
            with TabPane("Events", id="events"):
                yield VerticalScroll(
                    self.StaticWithLinkSupport(
                        self, classes="events tab_content_static"
                    )
                )

    def on_tabbed_content_tab_activated(
        self, event: TabbedContent.TabActivated
    ) -> None:
        """Refresh the active tab's content when switching tabs."""
        # Re-run watch_dom_node to refresh the newly visible tab's content.
        self.watch_dom_node(self.dom_node)

    # watch_dom_node helpers

    _STYLE_IGNORE_FRAMES: ClassVar[tuple[tuple[str, str], ...]] = (
        ("inspector.py", "set_rule"),
        ("styles.py", "set_rule"),
        ("inspector.py", "merge"),
        ("styles.py", "merge"),
        ("inspector.py", "merge_rules"),
        ("styles.py", "merge_rules"),
        ("_style_properties.py", "__set__"),
        ("dom.py", "display"),
        ("dom.py", "visible"),
        ("widget.py", "offset"),
    )

    @staticmethod
    def _wdn_format_location_info(
        location: "Tuple[str, int | None] | Literal['EDITED_WITH_INSPECTOR'] | None",
    ) -> Text:
        """Return a Rich Text link for a source location."""
        if location is None:
            return Text.styled("(unknown location)", "#808080")
        if location == "EDITED_WITH_INSPECTOR":
            return Text.styled("(edited)", "#808080")
        file, line_number = location
        action = f"open_file({file!r}, {line_number!r})"
        file_name = os.path.basename(file)
        location_string = (
            f"{file_name}:{line_number}" if line_number is not None else file_name
        )
        return Text.styled(location_string, Style(meta={"@click": action}))

    def _wdn_trace_inline_style(
        self,
        dom_node: "DOMNode",
        rule: str,
    ) -> "Tuple[str, int] | Literal['EDITED_WITH_INSPECTOR'] | None":
        """Return where a style rule was set inline, or None."""
        try:
            source = inline_style_call_stacks[dom_node]
            frame_infos = source[rule]
        except KeyError:
            return None
        frame_infos = [
            fi
            for fi in frame_infos
            if not any(
                fi.filename.endswith(fn) and fi.function == func
                for fn, func in self._STYLE_IGNORE_FRAMES
            )
        ]
        if not frame_infos:
            return None
        frame_info = frame_infos[0]
        if (
            frame_info.filename.endswith("inspector.py")
            and frame_info.function == "_apply_style_value"
        ):
            return "EDITED_WITH_INSPECTOR"
        return (frame_info.filename, frame_info.lineno)

    def _wdn_format_style_line(
        self,
        dom_node: "DOMNode",
        rule: str,
        styles: Styles,
        rules: RulesMap,
        inline: bool,
    ) -> Text:
        """Format a single CSS declaration line with optional source link."""
        single_rule_rules_map = RulesMap()
        single_rule_rules_map[rule] = rules[rule]
        important: Set[str] = set()
        if rule in styles.important:
            important.add(rule)
        single_rule_styles = Styles(
            node=styles.node, _rules=single_rule_rules_map, important=important
        )
        try:
            css_line = single_rule_styles.css_lines[0]
        except IndexError:
            return Text("")
        rule_hyphenated, value_and_semicolon = css_line.split(":", 1)
        rule_hyphenated = rule_hyphenated.strip()
        value_str = value_and_semicolon.strip()[:-1].strip()
        parsed_color: Color | None = None
        try:
            raw_value = rules[rule]
            if isinstance(raw_value, Color):
                parsed_color = raw_value
        except Exception as error:
            logger.debug("Inspector could not resolve CSS color", exc_info=error)
        optional_keyword, possible_color = (
            value_str.split(" ", 1) if " " in value_str else ("", value_str)
        )
        try:
            color = (
                parsed_color
                if parsed_color is not None
                else Color.parse(possible_color)
            )
            value_text = Text.styled(
                possible_color,
                Style.from_color(
                    bgcolor=color.rich_color, color=color.get_contrast_text().rich_color
                ),
            )
            value_text = Text.assemble(
                optional_keyword, " " if optional_keyword else "", value_text
            )
        except ColorParseError:
            value_text = Text(value_str)
        value_text.apply_meta({"rule": rule, "value": value_str, "inline": inline})
        suffix = (
            [
                "; ",
                self._wdn_format_location_info(
                    self._wdn_trace_inline_style(dom_node, rule)
                ),
            ]
            if inline
            else [";"]
        )
        return Text.assemble("  ", rule_hyphenated, ": ", value_text, *suffix, "\n")

    def _wdn_format_styles_block(
        self,
        dom_node: "DOMNode",
        styles: Styles,
        name: "Text | str",
        rule_set_location_info: "Text | None",
    ) -> Text:
        """Format a full CSS block (selector + declarations)."""
        inline = rule_set_location_info is None
        rules = styles.get_rules()
        return Text.assemble(
            name,
            " {",
            *(
                [" ", rule_set_location_info]
                if rule_set_location_info is not None
                else []
            ),
            "\n",
            Text().join(
                self._wdn_format_style_line(dom_node, rule, styles, rules, inline)
                for rule in rules
            ),
            "}",
        )

    @staticmethod
    def _wdn_resolve_rule_set_path(
        rule_set: RuleSet,
    ) -> "Tuple[str | None, int | None]":
        """Return (path, line_number) for a CSS rule set, or (None, None)."""
        path: str | None = None
        line_number: int | None = None
        try:
            stack = rule_set_call_stacks[rule_set]
            for frame_info in stack:
                if frame_info.function == "parse":
                    path = frame_info.frame.f_locals["path"]
                    assert isinstance(path, str)
                    break
        except KeyError:
            return None, None
        if path is None or ":" not in path:
            return path, None
        path, widget_name = path.rsplit(":", 1)
        try:
            with open(path, encoding="utf-8", errors="replace") as f:
                src_lines = f.readlines()
        except OSError:
            return path, None
        for i, line in enumerate(src_lines):
            if f"class {widget_name}" in line:
                line_number = i + 1
            if line_number is not None and "DEFAULT_CSS" in line:
                try:
                    import ast as _ast

                    tree = _ast.parse("".join(src_lines))
                    for node in _ast.walk(tree):
                        if isinstance(node, _ast.Assign) and any(
                            isinstance(t, _ast.Name) and t.id == "DEFAULT_CSS"
                            for t in node.targets
                        ):
                            line_number = node.lineno
                except Exception:
                    line_number = i + 1
                break
        return path, line_number

    def _wdn_update_styles(
        self,
        dom_node: "DOMNode",
        styles_static: "Static",
        applicable_rule_sets: "List[RuleSet]",
    ) -> None:
        """Render and display the styles panel for dom_node."""

        def format_rule_set(rule_set: RuleSet) -> Text:
            path, line_number = self._wdn_resolve_rule_set_path(rule_set)
            location = self._wdn_format_location_info(
                (path, line_number) if path else None
            )
            return self._wdn_format_styles_block(
                dom_node, rule_set.styles, rule_set.selectors, location
            )

        inline_style_text = self._wdn_format_styles_block(
            dom_node,
            dom_node.styles.inline,
            Text.styled("inline styles", "italic"),
            None,
        )
        styles_text = Text.assemble(
            inline_style_text,
            "\n\n",
            Text("\n\n").join(format_rule_set(rs) for rs in applicable_rule_sets),
        )
        styles_static.update(styles_text)

    def _wdn_update_key_bindings(
        self,
        dom_node: "DOMNode",
        key_bindings_data_table: "DataTable[Text | str]",
    ) -> None:
        """Populate the key bindings table for dom_node."""
        nodes_and_bindings = [
            (ancestor, binding)
            for ancestor in dom_node.ancestors_with_self
            for binding in ancestor._bindings.keys.values()
        ]
        key_bindings_data_table.clear(columns=True)
        key_bindings_data_table.add_columns(
            "Key", "Action", "Description", "Show", "Key Display", "Priority", "Source"
        )
        check_mark = Text("✅", style="#03AC13", justify="center")
        key_bindings_data_table.add_rows(
            [
                [
                    binding.key,
                    binding.action,
                    binding.description,
                    check_mark if binding.show else "",
                    (
                        (self.app.get_key_display(binding.key) or binding.key.upper())
                        if binding.key_display is None
                        else binding.key_display
                    ),
                    check_mark if binding.priority else "",
                    ancestor.css_identifier_styled,
                ]
                for (ancestor, binding) in nodes_and_bindings
            ]
        )

    @staticmethod
    def _wdn_format_object_location(obj: Any) -> Text:
        """Return a Rich Text link for the source location of an object."""
        try:
            line_number = inspect.getsourcelines(obj)[1]
            file = inspect.getsourcefile(obj)
            location: Tuple[str, int | None] | None = (
                (file, line_number) if file else None
            )
        except OSError as e:
            return Text.from_markup(
                f"[#808080](error getting location: [red]{escape(repr(e))}[/red])[/#808080]"
            )
        if location is None:
            return Text.styled("(unknown location)", "#808080")
        file2, line_number2 = location
        action = f"open_file({file2!r}, {line_number2!r})"
        file_name = os.path.basename(file2)
        location_string = (
            f"{file_name}:{line_number2}" if line_number2 is not None else file_name
        )
        return Text.styled(location_string, Style(meta={"@click": action}))

    def _wdn_message_info(
        self, dom_node: "DOMNode", message_class: "Type[Message]"
    ) -> Text:
        """Return a description of a message class, listing any handlers."""
        handler_name = message_class.handler_name
        handler_names = [handler_name, f"_{handler_name}"]
        potential_handlers = (
            dom_node.ancestors_with_self if message_class.bubble else [dom_node]
        )
        usages: List[Text] = []
        for ancestor in potential_handlers:
            for h_name in handler_names:
                if not hasattr(ancestor, h_name):
                    continue
                handler = getattr(ancestor, h_name)
                defining_class = handler.__self__.__class__
                def_location = self._wdn_format_object_location(handler)
                descendant_arrow = Text.styled(" > ", "#808080")
                dom_path = descendant_arrow.join(
                    [n.css_identifier_styled for n in ancestor.css_path_nodes]
                )
                link_id = self._link_id_counter
                self._link_id_counter += 1
                self._link_id_to_node[link_id] = ancestor
                dom_path.apply_meta({"@click": f"select_node({link_id})"})
                usages.append(
                    Text.assemble(
                        "🎯 ",
                        dom_path,
                        "\n\n",
                        f"{defining_class.__qualname__}.{h_name}",
                        " ",
                        def_location,
                    )
                )
        usage_info = (
            Text("\n\n").join(usages)
            if usages
            else Text(f"No listeners found for {' or '.join(handler_names)}")
        )
        doc = inspect.getdoc(message_class) or "(No docstring)"
        return Text.assemble(
            "📧 ",
            Text.styled(message_class.__qualname__, "bold"),
            " ",
            self._wdn_format_object_location(message_class),
            "\n",
            Text.styled(doc, "#808080"),
            "\n",
            usage_info,
            "\n",
        )

    def _wdn_update_events(
        self,
        dom_node: "DOMNode",
        events_static: "Static",
    ) -> None:
        """Populate the events panel for dom_node."""
        available_events: List[Type[Message]] = []
        seen: set = set()
        for cls in type(dom_node).__mro__:
            for value in cls.__dict__.values():
                if (
                    isinstance(value, type)
                    and issubclass(value, Message)
                    and value not in seen
                ):
                    available_events.append(value)
                    seen.add(value)
        try:
            import textual.events as _tevents

            for _name in dir(_tevents):
                _val = getattr(_tevents, _name)
                if (
                    isinstance(_val, type)
                    and issubclass(_val, Message)
                    and _val not in seen
                ):
                    available_events.append(_val)
                    seen.add(_val)
        except Exception as error:
            logger.debug("Textual event discovery was incomplete", exc_info=error)

        if available_events:
            events_static.update(
                Text("\n").join(
                    self._wdn_message_info(dom_node, ev) for ev in available_events
                )
            )
        else:
            events_static.update(
                f"(No message types exported by {type(dom_node).__name__!r} or its superclasses)"
            )

    def _get_rule_at(self, x: int, y: int) -> str | None:
        """Return the rule (property name) at the given absolute position, or None."""
        try:
            style = self.screen.get_style_at(x, y)
        except NoWidget:  # shouldn't really happen
            return None
        if "rule" in style.meta:
            return style.meta["rule"]
        else:
            return None

    def on_mouse_down(self, event: events.MouseDown) -> None:
        """Select a rule to edit."""
        widget, _ = self.screen.get_widget_at(*event.screen_offset)
        if widget is self._style_value_input:
            return
        self._apply_style_value()
        x, y = event.screen_offset
        rule = self._get_rule_at(x, y)
        if rule is not None:
            meta = self.screen.get_style_at(*event.screen_offset).meta
            assert "value" in meta, "Style meta has rule without value"
            assert "inline" in meta, "Style meta has rule without inline bool"
            if not meta["inline"]:
                return  # Editing stylesheet (non-inline) rules is not yet supported.
            input_parent = self.query_one("#styles VerticalScroll")
            input_parent.mount(self._style_value_input)  # before setting value
            input_parent.mount(self._style_value_error)
            self._style_value_input.display = True

            # Find leftmost and rightmost positions of the rule
            while x > 0 and self._get_rule_at(x - 1, y) == rule:
                x -= 1
            left = x
            right = input_parent.region.right
            self._style_value_input.styles.width = right - left
            # Position the input relative to the VerticalScroll container,
            # accounting for its scroll offset so it tracks the text correctly.
            scroll_y = input_parent.scroll_offset.y
            self._style_value_input.offset = (
                Offset(left, y + scroll_y) - input_parent.region.offset
            )
            self._style_value_input.value = meta["value"]
            self._style_value_input.focus()
            self._style_value_error.offset = Offset(
                0, y + scroll_y + 1 - input_parent.region.y
            )
            self._style_value_error.update("")
            self._editing_rule = rule

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Called when the user presses Enter in an input."""
        if event.input is self._style_value_input:
            self._apply_style_value()

    # NOTE: THIS FUNCTION'S NAME is relied upon by trace_inline_style
    def _apply_style_value(self) -> None:
        """Apply a new style value."""
        if self._editing_rule is None:
            return
        # Editing style sheet rules is not yet supported
        assert self.dom_node is not None, "editing style of no DOM node"
        declaration = f"{self._editing_rule}: {self._style_value_input.value};"
        # Based on the code in DOMQuery.set_styles
        try:
            new_styles = parse_declarations(declaration, path="set_styles")
        except TokenError as error:
            # Show only the concise error message, skipping the verbose "Error in stylesheet" header.
            message = str(error)
            final_message = "; ".join(part.strip() for part in message.split(";"))
            self._style_value_error.update(Text(final_message, style="red"))
            self._style_value_error.display = True
            return
        except DeclarationError as error:
            # error.name, error.token, error.message
            # error.message can be HelpText, a nice Rich renderable.
            self._style_value_error.update(error.message)
            self._style_value_error.display = True
            return

        # Tip: `merge` rather than `set_rule` allows a little trick of adding a new rule with
        # "<old rule value>; <new rule>: <new rule value>"
        # which is useful as a stopgap until there's a proper way to add new rules.

        # Prevent "(edited)" if the rule is unchanged.
        for rule in self.dom_node._inline_styles.get_rules():
            if new_styles.get_rule(rule) == self.dom_node._inline_styles.get_rule(rule):
                new_styles.clear_rule(rule)

        self.dom_node._inline_styles.merge(new_styles)
        self.dom_node.refresh(layout=True)
        self.watch_dom_node(self.dom_node)  # refresh the inspector
        self._style_value_input.display = False
        self._style_value_error.display = False
        self._editing_rule = None


class ResizeHandle(Widget):
    """A handle for resizing a panel.

    This should be a child of the panel.
    Therefore, one of the sides of the divide needs to be a container.
    It will be positioned on the edge of the panel according to the `side` parameter.
    The panel can use min-width, min-height, max-width, and max-height to limit the size.
    """

    DEFAULT_CSS = """
    ResizeHandle {
        width: auto;
        height: auto;
        background: $panel;
        color: rgba(128,128,128,0);
    }
    ResizeHandle:hover {
        background: $panel-lighten-1;
        color: rgba(128,128,128,0.3);
    }
    ResizeHandle.-active {
        background: $panel-darken-1;
    }
    """

    def __init__(
        self,
        target: Widget,
        side: Literal["left", "right", "top", "bottom"],
        *,
        name: str | None = None,
        widget_id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(name=name, id=widget_id, classes=classes, disabled=disabled)
        self._target = target
        self._resizing = False
        self._start_size: Size | None = None
        self._start_mouse_position: Offset | None = None
        self._side: Literal["left", "right", "top", "bottom"] = side
        self._horizontal_resize = side in ("left", "right")
        self.styles.dock = side

    def on_mouse_down(self, event: events.MouseDown) -> None:
        if self.disabled or self._resizing:
            return
        self.capture_mouse()
        self._resizing = True
        self._start_size = self._target.outer_size
        self._start_mouse_position = event.screen_offset
        self.add_class("-active")

    def on_mouse_up(self, event: events.MouseUp) -> None:
        self.release_mouse()
        self._resizing = False
        self._start_size = None
        self._start_mouse_position = None
        self.remove_class("-active")

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Resize the target widget as the mouse moves."""
        if not self._resizing:
            return
        assert self._start_size is not None and self._start_mouse_position is not None
        diff = event.screen_offset - self._start_mouse_position
        match self._side:
            case "left":
                self._target.styles.width = max(1, self._start_size.width - diff.x)
            case "right":
                self._target.styles.width = max(1, self._start_size.width + diff.x)
            case "top":
                new_height = self._start_size.height - diff.y
                # Clamp to the available space in the parent container so the widget
                # never grows offscreen (which breaks the scrollbar).
                if self._target.parent and isinstance(self._target.parent, Widget):
                    parent_h = self._target.parent.content_size.height
                    new_height = max(2, min(new_height, parent_h - 2))
                else:
                    new_height = max(2, new_height)
                self._target.styles.height = new_height
            case "bottom":
                self._target.styles.height = max(2, self._start_size.height + diff.y)

    def get_content_width(self, container: Size, _viewport: Size) -> int:
        return container.width if not self._horizontal_resize else 1

    def get_content_height(self, container: Size, _viewport: Size, width: int) -> int:
        return container.height if self._horizontal_resize else 1

    def render_line(self, y: int) -> Strip:
        char = "║" if self._horizontal_resize else "═" * self.size.width
        return Strip([Segment(char, self.rich_style)])


class OriginalStyles(NamedTuple):
    """The original styles of a widget before highlighting."""

    # border: BorderDefinition | None
    # """The original border of the widget."""
    # border_title: str | Text | None
    # """The original border title of the widget."""
    # background: Color | None
    # """The original background of the widget."""
    tint: Color | None
    """The original tint of the widget."""


ALLOW_INSPECTING_INSPECTOR = True
"""Whether widgets in the inspector can be picked for inspection."""


class Inspector(Container):
    """UI for inspecting the layout of the application."""

    DEFAULT_CSS = """
    Inspector {
        dock: right;
        width: 40;
        min-width: 15;
        border-left: wide $panel-darken-2;
        background: $panel;
    }
    Inspector Button.inspect_button {
        margin: 1;
        width: 1fr;
    }
    Inspector Button.inspect_button.picking {
        color: $accent;
    }
    Inspector DOMTree {
        height: 1fr;
        scrollbar-gutter: stable;
    }
    Inspector NodeInfo,
    Inspector TabbedContent,
    Inspector ContentSwitcher,
    Inspector TabPane,
    Inspector TabPane > VerticalScroll {
        width: 1fr !important;
        height: 1fr !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    Inspector .tab_content_static {
        margin-bottom: 1;
        link-color: $accent;
    }
    """

    picking = var(False)
    """Whether the user is picking a widget to inspect."""

    def __init__(self) -> None:
        """Initialise the inspector."""

        super().__init__()

        self._highlight_boxes: Dict[Widget, Dict[str, Container]] = {}
        """Extra elements added to highlight the border/margin/padding of the widget being inspected."""
        self._highlight_styles: Dict[Widget, OriginalStyles] = {}
        """Stores the original styles of any hovered widgets. Unrelated to _highlight_boxes."""

    def compose(self) -> ComposeResult:
        """Add sub-widgets."""
        inspect_icon = (
            "⇱"  # Alternatives: 🔍 🎯 🮰 🮵 ⮹ ⇱ 🢄 🡴 🡤 🡔 🢰 (↖️ arrow emoji unreliable)
        )
        # expand_icon = "+" # Alternatives: + ⨁ 🪜 🎊 🐡 🔬 (↕️ arrow emoji unreliable)
        yield Button(f"{inspect_icon} Inspect Element", classes="inspect_button")
        # yield Button(f"{expand_icon} Expand All Visible", classes="expand_all_button")
        yield DOMTree(self.app)
        yield NodeInfo()
        yield ResizeHandle(self, "left")

    def watch_picking(self, picking: bool) -> None:
        """Watch the picking variable."""
        self.reset_highlight()
        if picking:
            self.capture_mouse()
        else:
            self.release_mouse()
        self.query_one(".inspect_button", Button).set_class(picking, "picking")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle a button being clicked."""
        if event.button.has_class("expand_all_button"):
            self.query_one(DOMTree).root.expand_all()
        elif event.button.has_class("inspect_button"):
            self.picking = not self.picking

    def on_mouse_move(self, event: events.MouseMove) -> None:
        """Handle the mouse moving."""
        if not self.picking:
            return
        self.highlight(self.get_widget_under_mouse(event.screen_offset))

    def get_widget_under_mouse(self, screen_offset: Offset) -> Widget | None:
        """Get the widget under the mouse, ignoring the inspector's highlights and (optionally) the inspector panel."""
        for widget, _ in self.screen.get_widgets_at(*screen_offset):
            if widget.has_class("inspector_highlight") or (
                self in widget.ancestors_with_self and not ALLOW_INSPECTING_INSPECTOR
            ):
                continue
            return widget
        return None

    async def on_mouse_down(self, event: events.MouseDown) -> None:
        """Handle the mouse being pressed."""
        self.reset_highlight()
        if not self.picking:
            return
        leaf_widget = self.get_widget_under_mouse(event.screen_offset)
        self.picking = False

        if leaf_widget is None:
            return

        # `with self.prevent(DOMTree.Hovered):` would prevent the event from firing at all.
        # We just want to prevent the highlight from being shown in on_domtree_hovered.
        self._prevent_highlight = True

        # Expand the tree to the selected widget.
        await self.query_one(DOMTree).expand_to_dom_node(leaf_widget)

        def focus_and_clear_prevent_highlight() -> None:
            """Focus the DOMTree, and clear the _prevent_highlight flag. Both of these things seem to need a delay."""
            self.query_one(DOMTree).focus()
            if hasattr(self, "_prevent_highlight"):
                del self._prevent_highlight

        self.set_timer(0.1, focus_and_clear_prevent_highlight)

    def on_domtree_selected(self, event: DOMTree.Selected) -> None:
        """Handle a node being selected in the DOM tree."""
        self.query_one(NodeInfo).dom_node = event.dom_node

    def on_domtree_hovered(self, event: DOMTree.Hovered) -> None:
        """Handle a DOM node being hovered/highlighted."""
        self.highlight(event.dom_node)

    async def on_node_info_follow_link_to_node(
        self, event: NodeInfo.FollowLinkToNode
    ) -> None:
        """Handle a link being clicked in the NodeInfo panel."""
        await self.query_one(DOMTree).expand_to_dom_node(event.dom_node)

    def reset_highlight(self, except_widgets: Iterable[Widget] = ()) -> None:
        """Reset the highlight."""
        for widget in self._highlight_boxes:
            if widget in except_widgets:
                continue
            added_widgets = self._highlight_boxes[widget]
            for added_widget in added_widgets.values():
                added_widget.remove()
        for widget, old in list(self._highlight_styles.items()):
            if widget in except_widgets:
                continue
            # widget.styles.border = old.border
            # widget.border_title = old.border_title
            # widget.styles.background = old.background
            widget.styles.tint = old.tint
            del self._highlight_styles[widget]

    def is_list_of_widgets(self, value: Any) -> TypeGuard[List[Widget]]:
        """Test whether a value is a list of widgets. The TypeGuard tells the type checker that this function ensures the type."""
        if not isinstance(value, list):
            return False
        return all(isinstance(item, Widget) for item in value)

    def _tint_widgets(self, widgets: list) -> None:
        """Apply aquamarine tint to widgets, saving originals."""
        for widget in widgets:
            if widget in self._highlight_styles:
                continue
            self._highlight_styles[widget] = OriginalStyles(
                tint=widget.styles.inline.tint
                if widget.styles.inline.has_rule("tint")
                else None,
            )
            widget.styles.tint = Color.parse("aquamarine").with_alpha(0.5)

    def highlight(self, dom_node: DOMNode | None) -> None:
        """Highlight a DOM node."""
        if hasattr(self, "_prevent_highlight") and dom_node is not None:
            del self._prevent_highlight
            return

        if not isinstance(dom_node, Widget):
            self.reset_highlight()
            return

        widgets = dom_node.walk_children(with_self=True)
        assert self.is_list_of_widgets(widgets), (
            "walk_children should return a list of widgets, but got: " + repr(widgets)
        )
        self.reset_highlight(except_widgets=widgets)
        self._tint_widgets(widgets)

        # Highlight the clipped region and the box-model metrics of the hovered widget.
        if "inspector_highlight" not in self.app.styles.layers:
            self.app.styles.layers += ("inspector_highlight",)  # type: ignore

        if dom_node not in self._highlight_boxes:
            self._highlight_boxes[dom_node] = {}
        used_boxes: List[Container] = []

        def show_box(name: str, region: Region, color: str) -> None:
            """Draw a box to the screen, re-using an old one if possible."""
            assert isinstance(dom_node, Widget), (
                "dom_node needed for association with highlight box, but got: "
                + repr(dom_node)
            )
            try:
                box = self._highlight_boxes[dom_node][name]
            except KeyError:
                box = Container(classes="inspector_highlight")
                self._highlight_boxes[dom_node][name] = box
            box.styles.background = Color.parse(color).with_alpha(0.5)
            box.styles.width = region.width
            box.styles.height = region.height
            box.styles.offset = (region.x, region.y)
            box.styles.layer = "inspector_highlight"
            # box.styles.dock = "top" # "Literal['top']" is incompatible with "str | None"
            # box.styles.dock = cast(str, "top") # "str" is incompatible with "str | None"
            # box.styles.dock = cast(str | None, "top") # "str | None" is incompatible with "str | None"
            box.styles.dock = "top"
            self.app.mount(box)
            used_boxes.append(box)

        # show_box("region", dom_node.region, "blue")
        # show_box("scrollable_content_region", dom_node.scrollable_content_region, "red")
        try:
            map_geometry = self.screen.find_widget(dom_node)
        except NoWidget:
            return
        # Show the hovered widget's region, as it extends OUTSIDE of the clip region
        # (i.e. excluding what's normally visible, showing only the overflow),
        # and excluding the region of the inspector itself, since overlap causes confusion.
        regions = subtract_regions(
            map_geometry.region, [map_geometry.clip, self.region]
        )
        for index, region in enumerate(regions):
            show_box(f"clipped:{index}", region, "aquamarine")

        # Highlight box-model metrics: padding (green), border (yellow), margin (orange).
        try:
            padding = dom_node.styles.padding
            margin = dom_node.styles.margin
            base = map_geometry.region
            # Padding region (content area inset by border)
            pad_region = Region(
                base.x + padding.left,
                base.y + padding.top,
                max(0, base.width - padding.left - padding.right),
                max(0, base.height - padding.top - padding.bottom),
            )
            show_box("padding", pad_region, "green")
            # Margin region (area outside the widget)
            margin_region = Region(
                base.x - margin.left,
                base.y - margin.top,
                base.width + margin.left + margin.right,
                base.height + margin.top + margin.bottom,
            )
            show_box("margin", margin_region, "orange")
        except Exception as error:
            logger.debug("Widget box metrics are unavailable", exc_info=error)
        # remove unused boxes
        # including boxes associated with an old dom_node
        for dom_node, boxes in list(self._highlight_boxes.items()):
            for name, box in list(boxes.items()):
                if box not in used_boxes:
                    box.remove()
                    del self._highlight_boxes[dom_node][name]
            if not self._highlight_boxes[dom_node]:
                del self._highlight_boxes[dom_node]
