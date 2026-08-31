"""Tests for DPI scaling functionality in Paint tool."""

import sys
from unittest.mock import MagicMock, patch

from aura_cli.tui.tools.paint.paint import Paint


class TestDPIScaling:
    """Test DPI scaling detection and handling."""

    @patch("inspect.getfile", return_value="paint.py")
    def test_get_screen_size_macos(self, mock_getfile):
        """Test screen size detection on macOS."""
        mock_quartz = MagicMock()
        mock_quartz.CGMainDisplayID.return_value = 1

        mock_size = MagicMock()
        mock_size.width = 2560
        mock_size.height = 1440
        mock_quartz.CGDisplayBounds.return_value.size = mock_size

        with (
            patch("sys.platform", "darwin"),
            patch.dict(sys.modules, {"Quartz": mock_quartz}),
        ):
            paint = Paint()
            size = paint.get_screen_size()

            assert size.width == 2560
            assert size.height == 1440

    @patch("inspect.getfile", return_value="paint.py")
    def test_get_screen_size_fallback(self, mock_getfile):
        """Test screen size detection fallback to tkinter."""
        mock_tkinter = MagicMock()
        mock_root = MagicMock()
        mock_root.winfo_screenwidth.return_value = 1920
        mock_root.winfo_screenheight.return_value = 1080
        mock_tkinter.Tk.return_value = mock_root

        with (
            patch("sys.platform", "linux"),
            patch.dict(sys.modules, {"tkinter": mock_tkinter}),
        ):
            paint = Paint()
            size = paint.get_screen_size()

            assert size.width in [1920, 1280]

    @patch("inspect.getfile", return_value="paint.py")
    def test_get_screen_size_exception_handling(self, mock_getfile):
        """Test that exceptions in screen size detection are handled gracefully."""
        mock_tkinter = MagicMock()
        mock_tkinter.Tk.side_effect = Exception("Test error")

        with (
            patch("sys.platform", "linux"),
            patch.dict(sys.modules, {"tkinter": mock_tkinter}),
        ):
            paint = Paint()
            size = paint.get_screen_size()
            assert size.width > 0
            assert size.height > 0
