"""File Manager components.

Widgets and utilities for File Manager.

Components:
    FileBrowser: Main file browser widget
    FileContextMenu: Context menu for file operations
    RenameDialog: Dialog for renaming files
    NewFileDialog: Dialog for creating new files
    ConfirmDialog: Confirmation dialog
    PropertiesDialog: File properties dialog
    FileManagerStatusBar: Status bar widget
    FilePreview: File preview widget

Utilities:
    get_file_icon: Get icon for file type
    format_size: Format file size
    format_permissions: Format file permissions
    FILE_ICONS: Icon mapping dictionary
"""

# Import ConfirmDialog from shared dialogs
from aura_cli.tui.components.shared.dialogs import ConfirmDialog

from .dialogs import (
    FileContextMenu,
    NewFileDialog,
    PropertiesDialog,
    RenameDialog,
)
from .file_browser import (
    FILE_ICONS,
    FileBrowser,
    format_permissions,
    format_size,
    get_file_icon,
)
from .status_bar import FileManagerStatusBar, FilePreview

__all__ = [
    "FILE_ICONS",
    "ConfirmDialog",
    "FileBrowser",
    "FileContextMenu",
    "FileManagerStatusBar",
    "FilePreview",
    "NewFileDialog",
    "PropertiesDialog",
    "RenameDialog",
    "format_permissions",
    "format_size",
    "get_file_icon",
]
