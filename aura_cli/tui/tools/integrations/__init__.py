"""Tool integrations for Aura CLI.

Provides seamless integration between Aura CLI tools.

Features:
    - File Manager ↔ Paint: Open ANSI art files directly
    - Paint ↔ Export: Generate art from text/images
    - Cross-tool messaging and events
    - File type detection and routing
    - Extension compatibility checking

Constants:
    ANSI_ART_EXTENSIONS: Supported ANSI art file extensions
    IMAGE_EXTENSIONS: Supported image file extensions
    PAINT_EXTENSIONS: All paint-compatible extensions
"""

from __future__ import annotations

from pathlib import Path

__version__ = "0.2.0"

ANSI_ART_EXTENSIONS = {
    ".ans",
    ".ansi",
    ".txt",
    ".asc",
    ".nfo",
    ".diz",
    ".ice",
    ".idf",
    ".xb",
    ".bin",
}

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".bmp",
    ".webp",
    ".ico",
    ".svg",
    ".tiff",
    ".tif",
}

PAINT_EXTENSIONS = ANSI_ART_EXTENSIONS | IMAGE_EXTENSIONS


def is_paint_compatible(file_path: str) -> bool:
    """Check if file can be opened with AuraPaint.

    Args:
        file_path: Path to file to check

    Returns:
        True if file extension is paint-compatible
    """
    suffix = Path(file_path).suffix.lower()
    return suffix in PAINT_EXTENSIONS


def is_ansi_art(file_path: str) -> bool:
    """Check if file is ANSI art.

    Args:
        file_path: Path to file to check

    Returns:
        True if file extension is ANSI art format
    """
    suffix = Path(file_path).suffix.lower()
    return suffix in ANSI_ART_EXTENSIONS


__all__ = [
    "ANSI_ART_EXTENSIONS",
    "IMAGE_EXTENSIONS",
    "PAINT_EXTENSIONS",
    "is_ansi_art",
    "is_paint_compatible",
]
