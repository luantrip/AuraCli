"""Full-screen TUI surfaces."""

from aura_cli.tui.screens.constitution_screen import ConstitutionScreen
from aura_cli.tui.screens.diff_confirmation_screen import (
    DiffConfirmationScreen,
    generate_new_file_diff,
    generate_unified_diff,
)
from aura_cli.tui.screens.files_screen import FilesScreen
from aura_cli.tui.screens.paint_screen import PaintScreen
from aura_cli.tui.screens.settings_screen import SettingsScreen
from aura_cli.tui.screens.token_usage_screen import TokenUsageScreen
from aura_cli.tui.screens.tools_menu_screen import ToolsMenuScreen

__all__ = [
    "ConstitutionScreen",
    "DiffConfirmationScreen",
    "FilesScreen",
    "PaintScreen",
    "SettingsScreen",
    "TokenUsageScreen",
    "ToolsMenuScreen",
    "generate_new_file_diff",
    "generate_unified_diff",
]
