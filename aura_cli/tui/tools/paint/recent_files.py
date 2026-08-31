"""Recent Files Manager for Paint Tool.

Manages a list of recently opened files with persistent storage.
"""

import json
import logging
import os
from pathlib import Path
from typing import List

logger = logging.getLogger(__name__)
MAX_RECENT_FILES = 10


def get_recent_files_path() -> Path:
    """Get the path to the recent files storage file.

    Returns:
        Path to the recent files JSON file
    """
    from aura_cli.core.paths import aura_path

    config_dir = aura_path("paint")
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "recent_files.json"


def load_recent_files() -> List[str]:
    """Load the list of recent files.

    Returns:
        List of file paths, most recent first
    """
    recent_path = get_recent_files_path()
    if not recent_path.exists():
        return []

    try:
        with open(recent_path, encoding="utf-8") as f:
            data = json.load(f)
            files = data.get("files", [])
            return [f for f in files if os.path.exists(f)]
    except (json.JSONDecodeError, OSError):
        return []


def save_recent_files(files: List[str]) -> None:
    """Save the list of recent files.

    Args:
        files: List of file paths to save
    """
    recent_path = get_recent_files_path()
    try:
        with open(recent_path, "w", encoding="utf-8") as f:
            json.dump({"files": files}, f, indent=2)
    except OSError as error:
        logger.warning("Could not persist Paint recent files", exc_info=error)


def add_recent_file(file_path: str) -> None:
    """Add a file to the recent files list.

    Args:
        file_path: Path to the file to add
    """
    if not file_path or not os.path.exists(file_path):
        return

    file_path = os.path.abspath(file_path)
    files = load_recent_files()

    if file_path in files:
        files.remove(file_path)

    files.insert(0, file_path)
    files = files[:MAX_RECENT_FILES]

    save_recent_files(files)


def clear_recent_files() -> None:
    """Clear all recent files."""
    save_recent_files([])
