"""Animation Exporter - Aura CLI Paint Tool.

Provides export functionality for animations to multiple formats including
GIF, sprite sheets, and ANSI sequences.
"""

from typing import TYPE_CHECKING

try:
    from PIL import Image, ImageDraw

    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

if TYPE_CHECKING:
    from aura_cli.application.paint.animation import AnimationTimeline, Frame


class AnimationExporter:
    """Export animations to various formats.

    Supports:
        - GIF animation with frame timing
        - PNG sprite sheets with grid layout
        - ANSI escape sequence files
    """

    @staticmethod
    def export_gif(
        timeline: "AnimationTimeline",
        output_path: str,
        width: int = 640,
        height: int = 480,
        font_size: int = 12,
    ) -> bool:
        """Export animation as animated GIF.

        Args:
            timeline: Animation timeline to export
            output_path: Target file path for GIF
            width: Output width in pixels
            height: Output height in pixels
            font_size: Font size for text rendering

        Returns:
            True if export succeeded, False otherwise
        """
        if not PIL_AVAILABLE:
            return False

        try:
            frames_pil = []
            durations = []

            for frame in timeline.frames:
                img = AnimationExporter._frame_to_pil(frame, width, height, font_size)
                frames_pil.append(img)
                durations.append(frame.duration_ms)

            if frames_pil:
                frames_pil[0].save(
                    output_path,
                    save_all=True,
                    append_images=frames_pil[1:],
                    duration=durations,
                    loop=0 if timeline.loop else 1,
                    optimize=True,
                )

            return True
        except Exception:
            return False

    @staticmethod
    def export_sprite_sheet(
        timeline: "AnimationTimeline",
        output_path: str,
        frame_width: int = 160,
        frame_height: int = 120,
        columns: int = 8,
    ) -> bool:
        """Export animation as PNG sprite sheet.

        Arranges frames in a grid layout for use in game engines
        and animation tools.

        Args:
            timeline: Animation timeline to export
            output_path: Target file path for PNG
            frame_width: Width of each frame in pixels
            frame_height: Height of each frame in pixels
            columns: Number of columns in grid

        Returns:
            True if export succeeded, False otherwise
        """
        if not PIL_AVAILABLE:
            return False

        try:
            frame_count = len(timeline.frames)
            rows = (frame_count + columns - 1) // columns

            sheet_width = frame_width * columns
            sheet_height = frame_height * rows
            sheet = Image.new("RGB", (sheet_width, sheet_height), color="black")

            for i, frame in enumerate(timeline.frames):
                img = AnimationExporter._frame_to_pil(frame, frame_width, frame_height)

                col = i % columns
                row = i // columns
                x = col * frame_width
                y = row * frame_height

                sheet.paste(img, (x, y))

            sheet.save(output_path)
            return True
        except Exception:
            return False

    @staticmethod
    def export_ansi_sequence(timeline: "AnimationTimeline", output_path: str) -> bool:
        """Export animation as ANSI escape sequence file.

        Creates a text file with ANSI codes for terminal playback.

        Args:
            timeline: Animation timeline to export
            output_path: Target file path for ANSI file

        Returns:
            True if export succeeded, False otherwise
        """
        try:
            with open(output_path, "w", encoding="utf-8") as f:
                for frame in timeline.frames:
                    ansi_data = AnimationExporter._frame_to_ansi(frame)
                    f.write(ansi_data)
                    f.write(f"\n# Delay: {frame.duration_ms}ms\n")
                    f.write("\033[2J\033[H")

            return True
        except Exception:
            return False

    @staticmethod
    def _frame_to_pil(
        frame: "Frame", width: int, height: int, font_size: int = 12
    ) -> Image.Image:
        """Convert frame to PIL Image for rasterization.

        Args:
            frame: Frame to convert
            width: Output width in pixels
            height: Output height in pixels
            font_size: Font size for text rendering

        Returns:
            PIL Image object
        """
        img = Image.new("RGB", (width, height), color="#1E1E1E")
        draw = ImageDraw.Draw(img)

        if hasattr(frame, "layer_stack") and frame.layer_stack:
            composed = frame.layer_stack.compose()
            cell_width = width // len(composed[0]) if composed and composed[0] else 8
            cell_height = height // len(composed) if composed else 12

            for y, row in enumerate(composed):
                for x, cell in enumerate(row):
                    px = x * cell_width
                    py = y * cell_height

                    draw.rectangle(
                        [px, py, px + cell_width, py + cell_height], fill=cell.bg_color
                    )

        return img

    @staticmethod
    def _frame_to_ansi(frame: "Frame") -> str:
        """Convert frame to ANSI escape sequence string.

        Args:
            frame: Frame to convert

        Returns:
            ANSI-encoded string representation
        """
        if not hasattr(frame, "layer_stack") or not frame.layer_stack:
            return ""

        composed = frame.layer_stack.compose()
        lines = []

        for row in composed:
            line = ""
            for cell in row:
                line += (
                    f"\033[38;2;{cell.fg_color}\033[48;2;{cell.bg_color}m{cell.char}"
                )
            lines.append(line + "\033[0m")

        return "\n".join(lines)
