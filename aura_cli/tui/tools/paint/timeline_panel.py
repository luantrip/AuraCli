"""Timeline Panel Widget - Aura CLI Paint Tool.

Horizontal scrollable timeline for frame management with thumbnail previews
and frame manipulation controls.
"""

from typing import TYPE_CHECKING

from textual.app import ComposeResult
from textual.containers import Horizontal, ScrollableContainer, Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label, Static

if TYPE_CHECKING:
    from aura_cli.application.paint.animation import AnimationTimeline, Frame


class FrameThumbnail(Static):
    """Miniature frame representation in timeline.

    Displays frame number, duration, and visual indicator for active frame.
    """

    DEFAULT_CSS = """
    FrameThumbnail {
        width: 10;
        height: 5;
        background: #333333;
        border: solid #D3D3D3;
        margin: 0 1;
    }

    FrameThumbnail.active {
        border: solid #FF00FF;
        background: #1E1E1E;
    }
    """

    def __init__(self, frame: "Frame", is_active: bool = False) -> None:
        """Initialize frame thumbnail.

        Args:
            frame: Source frame to represent
            is_active: Whether this is the currently active frame
        """
        super().__init__()
        self.frame = frame
        self.is_active = is_active
        if is_active:
            self.add_class("active")

    def render(self) -> str:
        """Render frame information as text.

        Returns:
            Formatted string with frame number and duration
        """
        return f"Frame\n{self.frame.number}\n{self.frame.duration_ms}ms"


class TimelinePanel(Vertical):
    """Timeline panel widget for animation frame management.

    Features:
        - Horizontal scrollable frame list
        - Frame thumbnails with active indicator
        - Add/Delete/Duplicate frame controls
        - Reactive active frame tracking
        - Message-based event system
    """

    DEFAULT_CSS = """
    TimelinePanel {
        height: 12;
        background: #1E1E1E;
        border: solid #FF00FF;
    }

    TimelinePanel .header {
        height: 3;
        background: #333333;
        padding: 0 1;
    }

    TimelinePanel .header Label {
        color: #FFFFFF;
        width: 1fr;
    }

    TimelinePanel .header Button {
        margin: 0 1;
    }

    TimelinePanel .frames-container {
        height: 1fr;
        background: #1E1E1E;
    }
    """

    active_frame_index = reactive(0)

    class FrameChanged(Message):
        """Message posted when active frame changes.

        Attributes:
            frame_index: Index of newly active frame
        """

        def __init__(self, frame_index: int) -> None:
            self.frame_index = frame_index
            super().__init__()

    class FrameAdded(Message):
        """Message posted when new frame is added."""

    class FrameDeleted(Message):
        """Message posted when frame is deleted."""

    class FrameDuplicated(Message):
        """Message posted when frame is duplicated."""

    def __init__(self, timeline: "AnimationTimeline") -> None:
        """Initialize timeline panel.

        Args:
            timeline: Animation timeline to manage
        """
        super().__init__()
        self.timeline = timeline

    def compose(self) -> ComposeResult:
        """Compose timeline panel components."""
        yield Horizontal(
            Label("Timeline"),
            Button("Add", id="add_frame", variant="primary"),
            Button("Del", id="delete_frame"),
            Button("Dup", id="duplicate_frame"),
            classes="header",
        )
        yield ScrollableContainer(
            Horizontal(
                *self._create_frame_thumbnails(),
                id="frames_list",
            ),
            classes="frames-container",
        )

    def _create_frame_thumbnails(self) -> list:
        """Generate frame thumbnail widgets.

        Returns:
            List of FrameThumbnail widgets for all frames
        """
        return [
            FrameThumbnail(frame, i == self.active_frame_index)
            for i, frame in enumerate(self.timeline.frames)
        ]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle frame manipulation button presses.

        Args:
            event: Button press event
        """
        button_actions = {
            "add_frame": self.FrameAdded,
            "delete_frame": self.FrameDeleted,
            "duplicate_frame": self.FrameDuplicated,
        }

        message_class = button_actions.get(event.button.id)
        if message_class:
            self.post_message(message_class())

    def refresh_frames(self) -> None:
        """Refresh frame thumbnail display.

        Removes and recreates all frame thumbnails to reflect
        current timeline state.
        """
        frames_list = self.query_one("#frames_list")
        frames_list.remove_children()
        for thumb in self._create_frame_thumbnails():
            frames_list.mount(thumb)
