"""Tests for cli/ui/os_theme.py — cross-platform theme detection."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest

import aura_cli.cli.ui.os_theme as os_theme_mod


@pytest.fixture(autouse=True)
def clear_cache():
    os_theme_mod._cached_theme = None
    yield
    os_theme_mod._cached_theme = None


class TestDetectOsTheme:
    def test_returns_dark_or_light(self):
        with patch("aura_cli.cli.ui.os_theme.platform.system", return_value="Darwin"):
            with patch(
                "aura_cli.cli.ui.os_theme._detect_macos_theme", return_value="dark"
            ):
                result = os_theme_mod.detect_os_theme()
        assert result in ("dark", "light")

    def test_caches_result(self):
        with patch("aura_cli.cli.ui.os_theme.platform.system", return_value="Darwin"):
            with patch(
                "aura_cli.cli.ui.os_theme._detect_macos_theme", return_value="light"
            ) as m:
                os_theme_mod.detect_os_theme()
                os_theme_mod.detect_os_theme()
        m.assert_called_once()  # only called once despite two calls

    def test_cached_value_returned_directly(self):
        os_theme_mod._cached_theme = "light"
        with patch("aura_cli.cli.ui.os_theme.platform.system") as m:
            result = os_theme_mod.detect_os_theme()
        m.assert_not_called()
        assert result == "light"

    def test_unsupported_platform_fallback_dark(self):
        with patch("aura_cli.cli.ui.os_theme.platform.system", return_value="FreeBSD"):
            result = os_theme_mod.detect_os_theme()
        assert result == "dark"

    def test_exception_fallback_dark(self):
        with patch("aura_cli.cli.ui.os_theme.platform.system", return_value="Darwin"):
            with patch(
                "aura_cli.cli.ui.os_theme._detect_macos_theme",
                side_effect=RuntimeError("boom"),
            ):
                result = os_theme_mod.detect_os_theme()
        assert result == "dark"

    def test_linux_branch(self):
        with patch("aura_cli.cli.ui.os_theme.platform.system", return_value="Linux"):
            with patch(
                "aura_cli.cli.ui.os_theme._detect_linux_theme", return_value="light"
            ):
                result = os_theme_mod.detect_os_theme()
        assert result == "light"

    def test_windows_branch(self):
        with patch("aura_cli.cli.ui.os_theme.platform.system", return_value="Windows"):
            with patch(
                "aura_cli.cli.ui.os_theme._detect_windows_theme", return_value="dark"
            ):
                result = os_theme_mod.detect_os_theme()
        assert result == "dark"


class TestDetectMacosTheme:
    def test_dark_mode_when_key_exists(self):
        with patch(
            "aura_cli.cli.ui.os_theme.subprocess.check_output", return_value="Dark\n"
        ):
            result = os_theme_mod._detect_macos_theme()
        assert result == "dark"

    def test_light_mode_when_key_missing(self):
        with patch(
            "aura_cli.cli.ui.os_theme.subprocess.check_output",
            side_effect=subprocess.CalledProcessError(1, "defaults"),
        ):
            result = os_theme_mod._detect_macos_theme()
        assert result == "light"


class TestDetectLinuxTheme:
    def test_dark_gtk_theme(self):
        with patch(
            "aura_cli.cli.ui.os_theme.subprocess.check_output",
            return_value="'Adwaita-dark'\n",
        ):
            result = os_theme_mod._detect_linux_theme()
        assert result == "dark"

    def test_light_gtk_theme(self):
        with patch(
            "aura_cli.cli.ui.os_theme.subprocess.check_output",
            return_value="'Adwaita'\n",
        ):
            result = os_theme_mod._detect_linux_theme()
        assert result == "light"

    def test_gsettings_not_found_fallback_color_scheme_dark(self):
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FileNotFoundError("gsettings not found")
            return "'prefer-dark'\n"

        with patch(
            "aura_cli.cli.ui.os_theme.subprocess.check_output", side_effect=side_effect
        ):
            result = os_theme_mod._detect_linux_theme()
        assert result == "dark"

    def test_gsettings_not_found_fallback_color_scheme_light(self):
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise FileNotFoundError("gsettings not found")
            return "'default'\n"

        with patch(
            "aura_cli.cli.ui.os_theme.subprocess.check_output", side_effect=side_effect
        ):
            result = os_theme_mod._detect_linux_theme()
        assert result == "light"

    def test_both_gsettings_fail_returns_dark(self):
        with patch(
            "aura_cli.cli.ui.os_theme.subprocess.check_output",
            side_effect=FileNotFoundError,
        ):
            result = os_theme_mod._detect_linux_theme()
        assert result == "dark"

    def test_called_process_error_on_first_tries_color_scheme(self):
        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise subprocess.CalledProcessError(1, "gsettings")
            return "'prefer-dark'\n"

        with patch(
            "aura_cli.cli.ui.os_theme.subprocess.check_output", side_effect=side_effect
        ):
            result = os_theme_mod._detect_linux_theme()
        assert result == "dark"


class TestDetectWindowsTheme:
    def test_import_error_returns_dark(self):
        with patch.dict("sys.modules", {"winreg": None}):
            result = os_theme_mod._detect_windows_theme()
        assert result == "dark"

    def test_light_theme_value_1(self):
        mock_winreg = MagicMock()
        mock_winreg.OpenKey.return_value = MagicMock()
        mock_winreg.QueryValueEx.return_value = (1, None)
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = os_theme_mod._detect_windows_theme()
        assert result == "light"

    def test_dark_theme_value_0(self):
        mock_winreg = MagicMock()
        mock_winreg.OpenKey.return_value = MagicMock()
        mock_winreg.QueryValueEx.return_value = (0, None)
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = os_theme_mod._detect_windows_theme()
        assert result == "dark"

    def test_os_error_returns_dark(self):
        mock_winreg = MagicMock()
        mock_winreg.OpenKey.side_effect = OSError("no key")
        with patch.dict("sys.modules", {"winreg": mock_winreg}):
            result = os_theme_mod._detect_windows_theme()
        assert result == "dark"


class TestClearThemeCache:
    def test_clears_cached_value(self):
        os_theme_mod._cached_theme = "dark"
        os_theme_mod.clear_theme_cache()
        assert os_theme_mod._cached_theme is None

    def test_forces_redetection(self):
        os_theme_mod._cached_theme = "dark"
        os_theme_mod.clear_theme_cache()
        with patch("aura_cli.cli.ui.os_theme.platform.system", return_value="Darwin"):
            with patch(
                "aura_cli.cli.ui.os_theme._detect_macos_theme", return_value="light"
            ) as m:
                os_theme_mod.detect_os_theme()
        m.assert_called_once()
