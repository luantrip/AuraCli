"""Wallpaper - Aura CLI Paint Tool

Cross-platform desktop wallpaper management.

Features:
    - Multi-platform support (Windows, macOS, Linux)
    - Desktop environment detection (GNOME, KDE, XFCE, etc.)
    - Automatic configuration for 15+ desktop environments
    - Process detection for environment identification
"""

import logging
import os
from pathlib import Path
import subprocess
import sys

logger = logging.getLogger(__name__)


def _detect_linux_de() -> str:
    """Detect desktop environment on Linux."""
    desktop_session = os.environ.get("DESKTOP_SESSION", "").lower()
    _KNOWN = {
        "gnome",
        "unity",
        "cinnamon",
        "mate",
        "xfce4",
        "lxde",
        "fluxbox",
        "blackbox",
        "openbox",
        "icewm",
        "jwm",
        "afterstep",
        "trinity",
        "kde",
    }
    if desktop_session in _KNOWN:
        return desktop_session
    if "xfce" in desktop_session or desktop_session.startswith("xubuntu"):
        return "xfce4"
    if desktop_session.startswith("ubuntustudio"):
        return "kde"
    if desktop_session.startswith("ubuntu"):
        return "gnome"
    if desktop_session.startswith("lubuntu"):
        return "lxde"
    if desktop_session.startswith("kubuntu"):
        return "kde"
    if desktop_session.startswith("razor"):
        return "razor-qt"
    if desktop_session.startswith("wmaker"):
        return "windowmaker"
    if os.environ.get("KDE_FULL_SESSION") == "true":
        return "kde"
    gnome_id = os.environ.get("GNOME_DESKTOP_SESSION_ID", "")
    if gnome_id and "deprecated" not in gnome_id:
        return "gnome2"
    if is_running("xfce-mcs-manage"):
        return "xfce4"
    if is_running("ksmserver"):
        return "kde"
    return "unknown"


def get_desktop_environment() -> str:
    """Detect the current desktop environment."""
    if sys.platform in ["win32", "cygwin"]:
        return "windows"
    if sys.platform == "darwin":
        return "mac"
    return _detect_linux_de()


def is_running(process: str) -> bool:
    """Check if a process is currently running.

    Args:
        process: Process name to search for

    Returns:
        True if process found in process list

    Note:
        Uses basic text search, may have false positives.
    """
    if sys.platform == "win32":
        cmd = ["tasklist", "/v"]
    else:
        cmd = ["ps", "axw"]

    try:
        s = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        assert s.stdout is not None
        for x in s.stdout:
            # if re.search(process, x):
            if process in str(x):
                return True
    except FileNotFoundError:
        # This can happen if the command (e.g. 'ps') doesn't exist.
        return False
    return False


def _set_wallpaper_xfce4(file_loc: str, first_run: bool) -> None:
    if first_run:
        subprocess.Popen(
            [
                "xfconf-query",
                "-c",
                "xfce4-desktop",
                "-p",
                "/backdrop/screen0/monitor0/image-path",
                "-s",
                file_loc,
            ]
        )
        subprocess.Popen(
            [
                "xfconf-query",
                "-c",
                "xfce4-desktop",
                "-p",
                "/backdrop/screen0/monitor0/image-style",
                "-s",
                "3",
            ]
        )
        subprocess.Popen(
            [
                "xfconf-query",
                "-c",
                "xfce4-desktop",
                "-p",
                "/backdrop/screen0/monitor0/image-show",
                "-s",
                "true",
            ]
        )
    subprocess.Popen(["xfdesktop", "--reload"])


def _set_wallpaper_razor(file_loc: str, first_run: bool) -> None:
    if not first_run:
        return
    import configparser

    desktop_conf = configparser.ConfigParser()
    desktop_conf_file = os.path.join(get_config_dir("razor"), "desktop.conf")
    config_option = (
        R"screens\1\desktops\1\wallpaper"
        if os.path.isfile(desktop_conf_file)
        else R"desktops\1\wallpaper"
    )
    if not os.path.isfile(desktop_conf_file):
        desktop_conf_file = os.path.join(get_home_dir(), ".razor/desktop.conf")
    desktop_conf.read(desktop_conf_file)
    try:
        if desktop_conf.has_option("razor", config_option):
            desktop_conf.set("razor", config_option, file_loc)
            with open(desktop_conf_file, "w", encoding="utf-8", errors="replace") as f:
                desktop_conf.write(f)
    except Exception as error:
        logger.warning("Could not update Razor wallpaper configuration", exc_info=error)


def _set_wallpaper_linux(desktop_env: str, file_loc: str, first_run: bool) -> bool:
    """Set wallpaper on Linux desktop environments. Returns True on success."""
    _SIMPLE_CMDS = {
        "icewm": lambda: subprocess.Popen(["icewmbg", file_loc]),
        "blackbox": lambda: subprocess.Popen(["bsetbg", "-full", file_loc]),
        "lxde": lambda: subprocess.Popen(
            ["pcmanfm", "--set-wallpaper", file_loc, "--wallpaper-mode=scaled"]
        ),
        "windowmaker": lambda: subprocess.Popen(["wmsetbg", "-s", "-u", file_loc]),
    }
    if desktop_env in ["gnome", "unity", "cinnamon"]:
        uri = Path(file_loc).as_uri()
        SCHEMA = "org.gnome.desktop.background"
        try:
            from gi.repository import Gio  # type: ignore

            gsettings = Gio.Settings.new(SCHEMA)  # type: ignore
            gsettings.set_string("picture-uri", uri)
            gsettings.set_string("picture-uri-dark", uri)
        except Exception:
            subprocess.Popen(["gsettings", "set", SCHEMA, "picture-uri", uri])
            subprocess.Popen(["gsettings", "set", SCHEMA, "picture-uri-dark", uri])
    elif desktop_env == "mate":
        try:
            subprocess.Popen(
                [
                    "gsettings",
                    "set",
                    "org.mate.background",
                    "picture-filename",
                    file_loc,
                ]
            )
        except Exception:
            subprocess.Popen(
                [
                    "mateconftool-2",
                    "-t",
                    "string",
                    "--set",
                    "/desktop/mate/background/picture_filename",
                    file_loc,
                ]
            )
    elif desktop_env == "gnome2":
        subprocess.Popen(
            [
                "gconftool-2",
                "-t",
                "string",
                "--set",
                "/desktop/gnome/background/picture_filename",
                file_loc,
            ]
        )
    elif desktop_env in ["kde3", "trinity"]:
        subprocess.Popen(
            ["dcop", "kdesktop", "KBackgroundIface", "setWallpaper", "0", file_loc, "6"]
        )
    elif desktop_env == "xfce4":
        _set_wallpaper_xfce4(file_loc, first_run)
    elif desktop_env == "razor-qt":
        _set_wallpaper_razor(file_loc, first_run)
    elif desktop_env in ["fluxbox", "jwm", "openbox", "afterstep"]:
        try:
            subprocess.Popen(["fbsetbg", file_loc])
        except Exception:
            sys.stderr.write("ERROR: Failed to set wallpaper with fbsetbg!\n")
    elif desktop_env in _SIMPLE_CMDS:
        _SIMPLE_CMDS[desktop_env]()
    else:
        return False
    return True


def _set_wallpaper_mac(file_loc: str) -> None:
    try:
        from appscript import app, mactypes

        app("Finder").desktop_picture.set(mactypes.File(file_loc))
    except ImportError:
        OSASCRIPT = """
        on run (clp)
            if clp's length is not 1 then error "Incorrect Parameters"
            local file_loc
            set file_loc to clp's item 1
            tell application "Finder" to set desktop picture to POSIX file file_loc
        end run
        """
        subprocess.Popen(["osascript", "-e", OSASCRIPT, "--", file_loc])


def set_wallpaper(file_loc: str, first_run: bool = True):
    """Set desktop wallpaper to specified file."""
    desktop_env = get_desktop_environment()
    if desktop_env == "windows":
        import ctypes

        ctypes.windll.user32.SystemParametersInfoW(20, 0, file_loc, 0)  # type: ignore
        return True
    if desktop_env == "mac":
        _set_wallpaper_mac(file_loc)
        return True
    result = _set_wallpaper_linux(desktop_env, file_loc, first_run)
    if not result and first_run:
        sys.stderr.write(
            "Warning: Failed to set wallpaper. Your desktop environment is not supported."
        )
        sys.stderr.write(f"You can try manually to set your wallpaper to {file_loc}")
    return result


def get_config_dir(app_name: str) -> str:
    """Get application configuration directory path.

    Args:
        app_name: Application name for config subdirectory

    Returns:
        Full path to configuration directory

    Note:
        Respects XDG_CONFIG_HOME on Linux, APPDATA on Windows.
    """
    if "XDG_CONFIG_HOME" in os.environ:
        config_home = os.environ["XDG_CONFIG_HOME"]
    elif "APPDATA" in os.environ:  # On Windows
        config_home = os.environ["APPDATA"]
    else:
        try:
            from xdg import BaseDirectory

            config_home = BaseDirectory.xdg_config_home
        except ImportError:  # Most likely a Linux/Unix system anyway
            config_home = os.path.join(get_home_dir(), ".config")
    config_dir = os.path.join(config_home, app_name)
    return config_dir


def get_home_dir() -> str:
    """Get current user's home directory path.

    Returns:
        Expanded home directory path
    """
    return os.path.expanduser("~")
