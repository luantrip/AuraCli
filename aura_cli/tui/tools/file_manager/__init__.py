"""File Manager for Aura CLI.

Modern dual-pane file manager built with Textual.

Features:
    - Dual-pane navigation (Midnight Commander style)
    - Rich file icons and preview
    - Context menus for file operations
    - External editor integration
    - Clipboard support for copy/paste
    - File properties and metadata
    - Keyboard shortcuts and navigation

Components:
    FileManagerScreen: Main file manager screen
    FileBrowser: File browser widget
    FileContextMenu: Context menu for file operations
    FileManagerStatusBar: Status bar with file info
    FilePreview: File preview widget
"""

from __future__ import annotations

__version__ = "0.2.0"

try:
    from aura_cli.core.logger import get_logger as _get_logger

    _fm_logger = _get_logger(__name__)
except Exception:
    import logging as _logging

    _fm_logger = _logging.getLogger(__name__)

try:
    from .screens import FileManagerScreen
except ImportError as e:
    _fm_logger.warning("Could not import FileManagerScreen: %s", e)
    FileManagerScreen = None

try:
    # ConfirmDialog comes from shared dialogs
    from aura_cli.tui.components.shared.dialogs import ConfirmDialog

    from .components.file_browser import (
        FILE_ICONS,
        FileBrowser,
        FileContextMenu,
        NewFileDialog,
        PropertiesDialog,
        RenameDialog,
        format_size,
        get_file_icon,
    )
except ImportError as e:
    _fm_logger.warning("Could not import file_browser components: %s", e)
    FileBrowser = None
    FileContextMenu = None
    RenameDialog = None
    NewFileDialog = None
    ConfirmDialog = None
    PropertiesDialog = None
    get_file_icon = None
    format_size = None
    FILE_ICONS = {}

try:
    from .components.status_bar import FileManagerStatusBar, FilePreview
except ImportError as e:
    _fm_logger.warning("Could not import status_bar: %s", e)
    FileManagerStatusBar = None
    FilePreview = None

__all__ = [
    "FILE_ICONS",
    "ConfirmDialog",
    "FileBrowser",
    "FileContextMenu",
    "FileManagerScreen",
    "FileManagerStatusBar",
    "FilePreview",
    "NewFileDialog",
    "PropertiesDialog",
    "RenameDialog",
    "format_size",
    "get_file_icon",
]
