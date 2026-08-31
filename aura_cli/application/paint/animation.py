"""
Animation System for Paint Tool.

Provides frame-based animation support for ANSI art:
- Multiple frames with timing
- Animation playback controls
- Frame manipulation (copy, delete, reorder)
- Export to animated formats (GIF, ANSI animation)
- Onion skinning for animation preview
"""

from __future__ import annotations

import asyncio
import contextlib
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional
import uuid

from rich.style import Style

if TYPE_CHECKING:
    from .ansi_art_document import AnsiArtDocument
    from .layers import LayerStack


class PlaybackState(Enum):
    """Animation playback state."""

    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


class LoopMode(Enum):
    """Animation loop mode."""

    ONCE = "once"  # Play once and stop
    LOOP = "loop"  # Loop forever
    PING_PONG = "ping_pong"  # Play forward then backward


@dataclass
class Frame:
    """A single frame in an animation."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = "Frame"
    duration_ms: int = 100  # Duration in milliseconds

    # Frame data - can be either a flat document or layer stack
    width: int = 80
    height: int = 24
    ch: List[List[str]] = field(default_factory=list)
    st: List[List[Style]] = field(default_factory=list)

    # Optional layer data for complex frames
    layers_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Initialize frame data if empty."""
        if not self.ch:
            self.ch = [[" " for _ in range(self.width)] for _ in range(self.height)]
        if not self.st:
            default_style = Style(color="#ffffff", bgcolor="#000000")
            self.st = [
                [default_style for _ in range(self.width)] for _ in range(self.height)
            ]

    def copy(self) -> Frame:
        """Create a deep copy of this frame."""
        new_frame = Frame(
            name=f"{self.name} (copy)",
            duration_ms=self.duration_ms,
            width=self.width,
            height=self.height,
        )
        new_frame.ch = deepcopy(self.ch)
        new_frame.st = deepcopy(self.st)
        new_frame.layers_data = deepcopy(self.layers_data) if self.layers_data else None
        return new_frame

    def resize(self, new_width: int, new_height: int) -> None:
        """Resize the frame."""
        new_ch = [[" " for _ in range(new_width)] for _ in range(new_height)]
        default_style = Style(color="#ffffff", bgcolor="#000000")
        new_st = [[default_style for _ in range(new_width)] for _ in range(new_height)]

        for y in range(min(self.height, new_height)):
            for x in range(min(self.width, new_width)):
                new_ch[y][x] = self.ch[y][x]
                new_st[y][x] = self.st[y][x]

        self.width = new_width
        self.height = new_height
        self.ch = new_ch
        self.st = new_st

    def clear(self) -> None:
        """Clear the frame."""
        default_style = Style(color="#ffffff", bgcolor="#000000")
        for y in range(self.height):
            for x in range(self.width):
                self.ch[y][x] = " "
                self.st[y][x] = default_style

    @classmethod
    def from_document(
        cls, doc: AnsiArtDocument, name: str = "Frame", duration_ms: int = 100
    ) -> Frame:
        """Create a frame from an AnsiArtDocument."""
        frame = cls(
            name=name,
            duration_ms=duration_ms,
            width=doc.width,
            height=doc.height,
        )
        frame.ch = deepcopy(doc.ch)
        frame.st = deepcopy(doc.st)
        return frame

    def to_document(self) -> AnsiArtDocument:
        """Convert frame to an AnsiArtDocument."""
        from .ansi_art_document import AnsiArtDocument

        doc = AnsiArtDocument(self.width, self.height)
        doc.ch = deepcopy(self.ch)
        doc.st = deepcopy(self.st)
        return doc

    def to_dict(self) -> Dict[str, Any]:
        """Serialize frame to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "duration_ms": self.duration_ms,
            "width": self.width,
            "height": self.height,
            "ch": self.ch,
            "st": [
                [
                    {
                        "fg": style.color.name if style.color else "#ffffff",
                        "bg": style.bgcolor.name if style.bgcolor else "#000000",
                    }
                    for style in row
                ]
                for row in self.st
            ],
            "layers_data": self.layers_data,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Frame:
        """Deserialize frame from dictionary."""
        frame = cls(
            id=data["id"],
            name=data["name"],
            duration_ms=data["duration_ms"],
            width=data["width"],
            height=data["height"],
        )
        frame.ch = data["ch"]
        frame.st = [
            [Style(color=cell["fg"], bgcolor=cell["bg"]) for cell in row]
            for row in data["st"]
        ]
        frame.layers_data = data.get("layers_data")
        return frame


@dataclass
class OnionSkinSettings:
    """Settings for onion skinning."""

    enabled: bool = False
    frames_before: int = 2
    frames_after: int = 1
    opacity_before: float = 0.3
    opacity_after: float = 0.2
    color_before: str = "#ff0000"  # Red tint for previous frames
    color_after: str = "#00ff00"  # Green tint for next frames


class Animation:
    """Manages an animation sequence."""

    def __init__(self, width: int = 80, height: int = 24):
        self.width = width
        self.height = height
        self.name = "Untitled Animation"

        # Frame management
        self._frames: List[Frame] = []
        self._current_frame_index: int = 0

        # Playback settings
        self.loop_mode: LoopMode = LoopMode.LOOP
        self.playback_state: PlaybackState = PlaybackState.STOPPED
        self._playback_direction: int = 1  # 1 for forward, -1 for backward
        self._last_frame_time: float = 0

        # Onion skinning
        self.onion_skin = OnionSkinSettings()

        # Callbacks
        self._on_frame_change: List[Callable[[int], None]] = []
        self._on_playback_change: List[Callable[[PlaybackState], None]] = []

        # Create initial frame
        self.add_frame()

    @property
    def frame_count(self) -> int:
        """Get the number of frames."""
        return len(self._frames)

    @property
    def current_frame_index(self) -> int:
        """Get the current frame index."""
        return self._current_frame_index

    @property
    def current_frame(self) -> Optional[Frame]:
        """Get the current frame."""
        if 0 <= self._current_frame_index < len(self._frames):
            return self._frames[self._current_frame_index]
        return None

    @property
    def total_duration_ms(self) -> int:
        """Get the total animation duration in milliseconds."""
        return sum(f.duration_ms for f in self._frames)

    @property
    def fps(self) -> float:
        """Get the average frames per second."""
        if not self._frames:
            return 0
        avg_duration = self.total_duration_ms / len(self._frames)
        return 1000 / avg_duration if avg_duration > 0 else 0

    def add_frame(
        self,
        name: Optional[str] = None,
        duration_ms: int = 100,
        at_index: Optional[int] = None,
        copy_current: bool = False,
    ) -> Frame:
        """Add a new frame to the animation."""
        if name is None:
            name = f"Frame {len(self._frames) + 1}"

        if copy_current and self.current_frame:
            frame = self.current_frame.copy()
            frame.name = name
            frame.duration_ms = duration_ms
        else:
            frame = Frame(
                name=name,
                duration_ms=duration_ms,
                width=self.width,
                height=self.height,
            )

        if at_index is not None:
            self._frames.insert(at_index, frame)
        else:
            self._frames.append(frame)

        return frame

    def remove_frame(self, index: int) -> bool:
        """Remove a frame by index."""
        if len(self._frames) <= 1:
            return False  # Can't remove last frame

        if 0 <= index < len(self._frames):
            del self._frames[index]

            # Adjust current frame index
            if self._current_frame_index >= len(self._frames):
                self._current_frame_index = len(self._frames) - 1

            self._notify_frame_change()
            return True
        return False

    def duplicate_frame(self, index: int) -> Optional[Frame]:
        """Duplicate a frame."""
        if 0 <= index < len(self._frames):
            original = self._frames[index]
            copy = original.copy()
            self._frames.insert(index + 1, copy)
            return copy
        return None

    def move_frame(self, from_index: int, to_index: int) -> bool:
        """Move a frame to a new position."""
        if not (
            0 <= from_index < len(self._frames) and 0 <= to_index < len(self._frames)
        ):
            return False

        frame = self._frames.pop(from_index)
        self._frames.insert(to_index, frame)

        # Update current frame index if needed
        if from_index == self._current_frame_index:
            self._current_frame_index = to_index

        return True

    def get_frame(self, index: int) -> Optional[Frame]:
        """Get a frame by index."""
        if 0 <= index < len(self._frames):
            return self._frames[index]
        return None

    def set_current_frame(self, index: int) -> bool:
        """Set the current frame by index."""
        if 0 <= index < len(self._frames):
            self._current_frame_index = index
            self._notify_frame_change()
            return True
        return False

    def next_frame(self) -> bool:
        """Go to the next frame."""
        if self._current_frame_index < len(self._frames) - 1:
            self._current_frame_index += 1
            self._notify_frame_change()
            return True
        elif self.loop_mode == LoopMode.LOOP:
            self._current_frame_index = 0
            self._notify_frame_change()
            return True
        elif self.loop_mode == LoopMode.PING_PONG:
            self._playback_direction = -1
            return self.prev_frame()
        return False

    def prev_frame(self) -> bool:
        """Go to the previous frame."""
        if self._current_frame_index > 0:
            self._current_frame_index -= 1
            self._notify_frame_change()
            return True
        elif self.loop_mode == LoopMode.LOOP:
            self._current_frame_index = len(self._frames) - 1
            self._notify_frame_change()
            return True
        elif self.loop_mode == LoopMode.PING_PONG:
            self._playback_direction = 1
            return self.next_frame()
        return False

    def first_frame(self) -> None:
        """Go to the first frame."""
        self._current_frame_index = 0
        self._notify_frame_change()

    def last_frame(self) -> None:
        """Go to the last frame."""
        self._current_frame_index = len(self._frames) - 1
        self._notify_frame_change()

    # ═══════════════════════════════════════════════════════════════════════════
    # Playback Control
    # ═══════════════════════════════════════════════════════════════════════════

    def play(self) -> None:
        """Start playing the animation."""
        self.playback_state = PlaybackState.PLAYING
        self._last_frame_time = time.time() * 1000
        self._notify_playback_change()

    def pause(self) -> None:
        """Pause the animation."""
        self.playback_state = PlaybackState.PAUSED
        self._notify_playback_change()

    def stop(self) -> None:
        """Stop the animation and return to first frame."""
        self.playback_state = PlaybackState.STOPPED
        self._current_frame_index = 0
        self._playback_direction = 1
        self._notify_frame_change()
        self._notify_playback_change()

    def toggle_playback(self) -> None:
        """Toggle between play and pause."""
        if self.playback_state == PlaybackState.PLAYING:
            self.pause()
        else:
            self.play()

    def update(self) -> bool:
        """Update animation state. Returns True if frame changed."""
        if self.playback_state != PlaybackState.PLAYING:
            return False

        current_time = time.time() * 1000
        current_frame = self.current_frame

        if not current_frame:
            return False

        elapsed = current_time - self._last_frame_time

        if elapsed >= current_frame.duration_ms:
            self._last_frame_time = current_time

            if self._playback_direction > 0:
                if not self.next_frame() and self.loop_mode == LoopMode.ONCE:
                    self.stop()
            else:
                if not self.prev_frame() and self.loop_mode == LoopMode.ONCE:
                    self.stop()

            return True

        return False

    async def play_async(
        self, callback: Optional[Callable[[Frame], None]] = None
    ) -> None:
        """Play animation asynchronously."""
        self.play()

        while self.playback_state == PlaybackState.PLAYING:
            if self.update() and callback and self.current_frame:
                callback(self.current_frame)

            # Sleep for a short time to prevent busy-waiting
            await asyncio.sleep(0.01)

    # ═══════════════════════════════════════════════════════════════════════════
    # Onion Skinning
    # ═══════════════════════════════════════════════════════════════════════════

    def get_onion_skin_frames(self) -> List[tuple]:
        """Get frames for onion skinning. Returns list of (frame, opacity, tint)."""
        if not self.onion_skin.enabled:
            return []

        result = []

        # Previous frames (red tint)
        for i in range(1, self.onion_skin.frames_before + 1):
            idx = self._current_frame_index - i
            if idx >= 0:
                opacity = self.onion_skin.opacity_before * (
                    1 - i / (self.onion_skin.frames_before + 1)
                )
                result.append(
                    (self._frames[idx], opacity, self.onion_skin.color_before)
                )

        # Next frames (green tint)
        for i in range(1, self.onion_skin.frames_after + 1):
            idx = self._current_frame_index + i
            if idx < len(self._frames):
                opacity = self.onion_skin.opacity_after * (
                    1 - i / (self.onion_skin.frames_after + 1)
                )
                result.append((self._frames[idx], opacity, self.onion_skin.color_after))

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Export
    # ═══════════════════════════════════════════════════════════════════════════

    def export_gif(self, output_path: Path) -> bool:
        """Export animation as GIF."""
        try:
            from PIL import Image

            images = []
            durations = []

            for frame in self._frames:
                # Convert frame to image
                img = Image.new("RGB", (frame.width * 8, frame.height * 16), (0, 0, 0))
                # This is a simplified version - full implementation would render text
                images.append(img)
                durations.append(frame.duration_ms)

            if images:
                images[0].save(
                    output_path,
                    save_all=True,
                    append_images=images[1:],
                    duration=durations,
                    loop=0 if self.loop_mode == LoopMode.LOOP else 1,
                )
                return True
            return False

        except Exception as e:
            print(f"Error exporting GIF: {e}")
            return False

    def export_ansi_sequence(self, output_path: Path) -> bool:
        """Export animation as ANSI escape sequence file."""
        try:
            content = []

            # Clear screen and hide cursor
            content.append("\033[2J\033[?25l")

            for frame in self._frames:
                # Move cursor to top-left
                content.append("\033[H")

                # Render frame
                doc = frame.to_document()
                frame_content = doc.encode_to_format("ANSI")
                content.append(frame_content.decode("utf-8"))

                # Add delay (using ANSI timing if supported)
                # Note: Most terminals don't support timing in ANSI files
                content.append(f"\033[{frame.duration_ms}ms")

            # Show cursor
            content.append("\033[?25h")

            output_path.write_text("".join(content))
            return True

        except Exception as e:
            print(f"Error exporting ANSI sequence: {e}")
            return False

    def export_frame_sequence(
        self, output_dir: Path, output_format: str = "ANSI"
    ) -> bool:
        """Export each frame as a separate file."""
        try:
            output_dir.mkdir(parents=True, exist_ok=True)

            for i, frame in enumerate(self._frames):
                doc = frame.to_document()
                filename = f"frame_{i:04d}.{output_format.lower()}"
                filepath = output_dir / filename

                content = doc.encode_to_format(output_format)

                if isinstance(content, bytes):
                    filepath.write_bytes(content)
                else:
                    filepath.write_text(content)

            return True

        except Exception as e:
            print(f"Error exporting frame sequence: {e}")
            return False

    # ═══════════════════════════════════════════════════════════════════════════
    # Serialization
    # ═══════════════════════════════════════════════════════════════════════════

    def to_dict(self) -> Dict[str, Any]:
        """Serialize animation to dictionary."""
        return {
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "loop_mode": self.loop_mode.value,
            "frames": [f.to_dict() for f in self._frames],
            "onion_skin": {
                "enabled": self.onion_skin.enabled,
                "frames_before": self.onion_skin.frames_before,
                "frames_after": self.onion_skin.frames_after,
                "opacity_before": self.onion_skin.opacity_before,
                "opacity_after": self.onion_skin.opacity_after,
                "color_before": self.onion_skin.color_before,
                "color_after": self.onion_skin.color_after,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Animation:
        """Deserialize animation from dictionary."""
        anim = cls(data["width"], data["height"])
        anim.name = data["name"]
        anim.loop_mode = LoopMode(data["loop_mode"])

        # Load frames
        anim._frames = [Frame.from_dict(f) for f in data["frames"]]

        # Load onion skin settings
        if "onion_skin" in data:
            os_data = data["onion_skin"]
            anim.onion_skin = OnionSkinSettings(
                enabled=os_data.get("enabled", False),
                frames_before=os_data.get("frames_before", 2),
                frames_after=os_data.get("frames_after", 1),
                opacity_before=os_data.get("opacity_before", 0.3),
                opacity_after=os_data.get("opacity_after", 0.2),
                color_before=os_data.get("color_before", "#ff0000"),
                color_after=os_data.get("color_after", "#00ff00"),
            )

        return anim

    def save(self, filepath: Path) -> bool:
        """Save animation to file."""
        try:
            data = self.to_dict()
            filepath.write_text(json.dumps(data, indent=2))
            return True
        except Exception as e:
            print(f"Error saving animation: {e}")
            return False

    @classmethod
    def load(cls, filepath: Path) -> Optional[Animation]:
        """Load animation from file."""
        try:
            data = json.loads(filepath.read_text())
            return cls.from_dict(data)
        except Exception as e:
            print(f"Error loading animation: {e}")
            return None

    # ═══════════════════════════════════════════════════════════════════════════
    # Event Handling
    # ═══════════════════════════════════════════════════════════════════════════

    def on_frame_change(self, callback: Callable[[int], None]) -> None:
        """Register a callback for frame changes."""
        self._on_frame_change.append(callback)

    def on_playback_change(self, callback: Callable[[PlaybackState], None]) -> None:
        """Register a callback for playback state changes."""
        self._on_playback_change.append(callback)

    def _notify_frame_change(self) -> None:
        """Notify callbacks of frame change."""
        for callback in self._on_frame_change:
            with contextlib.suppress(Exception):
                callback(self._current_frame_index)

    def _notify_playback_change(self) -> None:
        """Notify callbacks of playback state change."""
        for callback in self._on_playback_change:
            with contextlib.suppress(Exception):
                callback(self.playback_state)

    def resize(self, new_width: int, new_height: int) -> None:
        """Resize all frames."""
        self.width = new_width
        self.height = new_height

        for frame in self._frames:
            frame.resize(new_width, new_height)


@dataclass
class AnimationFrame:
    """Animation frame with layer stack support."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    number: int = 1
    duration_ms: int = 100
    layer_stack: Optional[LayerStack] = None

    def duplicate(self) -> AnimationFrame:
        return AnimationFrame(
            number=self.number,
            duration_ms=self.duration_ms,
            layer_stack=deepcopy(self.layer_stack),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "number": self.number,
            "duration_ms": self.duration_ms,
            "layer_stack": self.layer_stack.to_dict() if self.layer_stack else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AnimationFrame:
        from .layers import LayerStack

        return cls(
            id=data["id"],
            number=data["number"],
            duration_ms=data["duration_ms"],
            layer_stack=(
                LayerStack.from_dict(data["layer_stack"])
                if data.get("layer_stack")
                else None
            ),
        )


class AnimationTimeline:
    """Timeline manager for animation."""

    def __init__(self):
        self.frames: List[AnimationFrame] = []
        self.active_frame_index: int = 0
        self.fps: int = 12
        self.loop: bool = True
        self.is_playing: bool = False

    @property
    def active_frame(self) -> Optional[AnimationFrame]:
        return (
            self.frames[self.active_frame_index]
            if 0 <= self.active_frame_index < len(self.frames)
            else None
        )

    @property
    def frame_count(self) -> int:
        return len(self.frames)

    @property
    def total_duration_ms(self) -> int:
        return sum(f.duration_ms for f in self.frames)

    def add_frame(self, frame: Optional[AnimationFrame] = None) -> AnimationFrame:
        if frame is None:
            frame = AnimationFrame(number=len(self.frames) + 1)
        self.frames.append(frame)
        self._renumber_frames()
        return frame

    def insert_frame(
        self, index: int, frame: Optional[AnimationFrame] = None
    ) -> AnimationFrame:
        if frame is None:
            frame = AnimationFrame()
        self.frames.insert(index, frame)
        self._renumber_frames()
        return frame

    def delete_frame(self, index: int) -> bool:
        if 0 <= index < len(self.frames) and len(self.frames) > 1:
            del self.frames[index]
            self._renumber_frames()
            if self.active_frame_index >= len(self.frames):
                self.active_frame_index = len(self.frames) - 1
            return True
        return False

    def duplicate_frame(self, index: int) -> Optional[AnimationFrame]:
        if 0 <= index < len(self.frames):
            new_frame = self.frames[index].duplicate()
            self.frames.insert(index + 1, new_frame)
            self._renumber_frames()
            return new_frame
        return None

    def move_frame(self, from_index: int, to_index: int) -> bool:
        if 0 <= from_index < len(self.frames) and 0 <= to_index < len(self.frames):
            frame = self.frames.pop(from_index)
            self.frames.insert(to_index, frame)
            self._renumber_frames()
            if self.active_frame_index == from_index:
                self.active_frame_index = to_index
            return True
        return False

    def set_active_frame(self, index: int) -> bool:
        if 0 <= index < len(self.frames):
            self.active_frame_index = index
            return True
        return False

    def next_frame(self) -> bool:
        if self.active_frame_index < len(self.frames) - 1:
            self.active_frame_index += 1
            return True
        elif self.loop:
            self.active_frame_index = 0
            return True
        return False

    def previous_frame(self) -> bool:
        if self.active_frame_index > 0:
            self.active_frame_index -= 1
            return True
        elif self.loop:
            self.active_frame_index = len(self.frames) - 1
            return True
        return False

    def _renumber_frames(self):
        for i, frame in enumerate(self.frames, 1):
            frame.number = i

    def to_dict(self) -> dict:
        return {
            "frames": [f.to_dict() for f in self.frames],
            "active_frame_index": self.active_frame_index,
            "fps": self.fps,
            "loop": self.loop,
        }

    @classmethod
    def from_dict(cls, data: dict) -> AnimationTimeline:
        timeline = cls()
        timeline.frames = [AnimationFrame.from_dict(f) for f in data["frames"]]
        timeline.active_frame_index = data["active_frame_index"]
        timeline.fps = data["fps"]
        timeline.loop = data["loop"]
        return timeline
