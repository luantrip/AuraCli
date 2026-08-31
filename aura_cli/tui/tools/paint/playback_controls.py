"""Playback Controls Widget - Aura CLI Paint Tool.

Asynchronous animation playback controls with FPS adjustment and loop toggle.
"""

import asyncio

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Label


class PlaybackControls(Horizontal):
    """Animation playback control widget with async playback engine.

    Features:
        - Play/Pause/Stop controls
        - Loop toggle
        - FPS adjustment (1-60 FPS)
        - Frame counter display
        - Async playback worker with @work decorator
        - Exclusive worker to prevent concurrent playback
    """

    DEFAULT_CSS = """
    PlaybackControls {
        height: 3;
        background: #1E1E1E;
        border: solid #333333;
        padding: 0 1;
    }

    PlaybackControls Button {
        margin: 0 1;
        background: #333333;
        color: #FFFFFF;
    }

    PlaybackControls Button.active {
        background: #FF00FF;
    }

    PlaybackControls Label {
        color: #D3D3D3;
        margin: 0 1;
    }
    """

    is_playing = reactive(False)
    fps = reactive(12)
    loop = reactive(True)
    current_frame = reactive(0)
    total_frames = reactive(1)

    class PlaybackStarted(Message):
        """Message posted when playback starts."""

    class PlaybackPaused(Message):
        """Message posted when playback pauses."""

    class PlaybackStopped(Message):
        """Message posted when playback stops."""

    class FrameAdvanced(Message):
        """Message posted when frame advances during playback.

        Attributes:
            frame_index: Index of newly active frame
        """

        def __init__(self, frame_index: int) -> None:
            self.frame_index = frame_index
            super().__init__()

    class LoopToggled(Message):
        """Message posted when loop mode toggles.

        Attributes:
            loop: Whether loop mode is enabled
        """

        def __init__(self, loop: bool) -> None:
            self.loop = loop
            super().__init__()

    def compose(self) -> ComposeResult:
        """Compose playback control components."""
        yield Button("▶", id="play", variant="primary")
        yield Button("⏸", id="pause")
        yield Button("⏹", id="stop")
        yield Button("⟳", id="loop", classes="active" if self.loop else "")
        yield Label(
            f"Frame: {self.current_frame + 1}/{self.total_frames}", id="frame_counter"
        )
        yield Label(f"FPS: {self.fps}", id="fps_display")
        yield Button("-", id="fps_down")
        yield Button("+", id="fps_up")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press events.

        Args:
            event: Button press event
        """
        button_actions = {
            "play": self.action_play,
            "pause": self.action_pause,
            "stop": self.action_stop,
            "loop": self._toggle_loop,
            "fps_down": lambda: self._adjust_fps(-1),
            "fps_up": lambda: self._adjust_fps(1),
        }

        action = button_actions.get(event.button.id)
        if action:
            action()

    def _toggle_loop(self) -> None:
        """Toggle loop mode and update button visual state."""
        self.loop = not self.loop
        loop_button = self.query_one("#loop", Button)

        if self.loop:
            loop_button.add_class("active")
        else:
            loop_button.remove_class("active")

        self.post_message(self.LoopToggled(self.loop))

    def _adjust_fps(self, delta: int) -> None:
        """Adjust FPS within valid range.

        Args:
            delta: FPS adjustment amount (+1 or -1)
        """
        self.fps = max(1, min(60, self.fps + delta))
        self.query_one("#fps_display", Label).update(f"FPS: {self.fps}")

    def action_play(self) -> None:
        """Start playback if not already playing."""
        if not self.is_playing:
            self.is_playing = True
            self.post_message(self.PlaybackStarted())
            self._start_playback()

    def action_pause(self) -> None:
        """Pause playback."""
        self.is_playing = False
        self.post_message(self.PlaybackPaused())

    def action_stop(self) -> None:
        """Stop playback and reset to first frame."""
        self.is_playing = False
        self.current_frame = 0
        self.post_message(self.PlaybackStopped())
        self._update_frame_counter()

    @work(exclusive=True)
    async def _start_playback(self) -> None:
        """Asynchronous playback loop worker.

        Runs exclusively to prevent concurrent playback instances.
        Advances frames based on FPS and handles loop/stop logic.
        """
        while self.is_playing:
            await asyncio.sleep(1.0 / self.fps)

            self.current_frame += 1
            if self.current_frame >= self.total_frames:
                if self.loop:
                    self.current_frame = 0
                else:
                    self.is_playing = False
                    break

            self.post_message(self.FrameAdvanced(self.current_frame))
            self._update_frame_counter()

    def _update_frame_counter(self) -> None:
        """Update frame counter display with current position."""
        counter = self.query_one("#frame_counter", Label)
        counter.update(f"Frame: {self.current_frame + 1}/{self.total_frames}")
