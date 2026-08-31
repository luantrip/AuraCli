"""Monitor tool for Aura CLI — terminal-based web browser and content monitor.

Wraps Chawan for text-based browsing (HTML/Markdown/Gemini rendering), live
content monitoring, API response visualisation and real-time log streaming.
Supports full-screen (Ctrl+M) and embedded widget modes.
Config stored in ~/.config/aura/monitor.toml.
"""

from dataclasses import dataclass, field
from enum import Enum
import os
from pathlib import Path
import shutil
import subprocess
from typing import Any, Callable, Dict, List, Optional

__all__ = [
    "MONITOR_AVAILABLE",
    "MonitorConfig",
    "MonitorContent",
    "MonitorMode",
    "MonitorSession",
    "get_monitor_binary",
    "launch_monitor",
    "render_content",
]

# =============================================================================
# CONSTANTS
# =============================================================================


# Check for Chawan binary
def _find_chawan_binary() -> Optional[str]:
    """Find the Chawan browser binary."""
    # Start from project root relative to this file
    # aura_cli/tui/tools/monitor/__init__.py -> 4 levels up -> project root
    project_root = Path(__file__).parent.parent.parent.parent.parent

    # Check common locations
    locations = [
        # Check project bin/aura-monitor
        str(project_root / "bin" / "aura-monitor"),
        # Check system path for aura-monitor
        shutil.which("aura-monitor"),
        # Legacy checks
        shutil.which("cha"),
        shutil.which("chawan"),
        os.path.expanduser("~/.local/bin/cha"),
        "/usr/local/bin/cha",
        # Check in tools_tui dev paths
        str(project_root / "tools_tui/monitor/target/release/bin/cha"),
        str(project_root / "tools_tui/monitor/cha"),
    ]

    for loc in locations:
        if loc and os.path.isfile(loc) and os.access(loc, os.X_OK):
            return loc

    return None


CHAWAN_BINARY = _find_chawan_binary()
MONITOR_AVAILABLE = CHAWAN_BINARY is not None


def get_monitor_binary(*, refresh: bool = False) -> Optional[str]:
    """Get the monitor binary, optionally refreshing its availability."""
    global CHAWAN_BINARY, MONITOR_AVAILABLE
    if refresh:
        CHAWAN_BINARY = _find_chawan_binary()
        MONITOR_AVAILABLE = CHAWAN_BINARY is not None
    return CHAWAN_BINARY


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================


class MonitorMode(Enum):
    """Monitor display modes."""

    BROWSER = "browser"  # Full web browser
    DUMP = "dump"  # Dump content to text
    HEADLESS = "headless"  # Headless mode for API calls
    WATCH = "watch"  # Live monitoring mode


class ContentType(Enum):
    """Supported content types."""

    HTML = "text/html"
    MARKDOWN = "text/markdown"
    PLAIN = "text/plain"
    JSON = "application/json"
    GEMINI = "text/gemini"
    GOPHER = "text/gopher"


@dataclass
class MonitorConfig:
    """Configuration for the monitor."""

    # Display settings
    color_mode: str = "auto"  # auto, true, 256, 16, mono
    image_mode: str = "auto"  # auto, sixel, kitty, none
    columns: int = 80
    lines: int = 24

    # Network settings
    user_agent: str = "Aura-Monitor/1.0"
    timeout: int = 30
    max_redirects: int = 10

    # Features
    cookies: bool = False
    javascript: bool = False
    images: bool = False

    # Appearance
    highlight_color: str = "cyan"
    background: str = "default"

    # Paths
    config_dir: Path = field(
        default_factory=lambda: Path.home() / ".config/aura/monitor"
    )
    cache_dir: Path = field(default_factory=lambda: Path.home() / ".cache/aura/monitor")

    def to_args(self) -> List[str]:
        """Convert config to command-line arguments."""
        args = []

        if self.color_mode != "auto":
            args.extend(["-o", f"display.color-mode = '{self.color_mode}'"])

        if not self.cookies:
            args.extend(["-o", "buffer.cookie = false"])

        if not self.javascript:
            args.extend(["-o", "buffer.scripting = false"])

        if not self.images:
            args.extend(["-o", "buffer.images = false"])

        args.extend(["-o", f"display.columns = {self.columns}"])
        args.extend(["-o", f"display.lines = {self.lines}"])

        return args


@dataclass
class MonitorContent:
    """Represents content fetched by the monitor."""

    url: str
    content_type: ContentType
    text: str
    title: str = ""
    status_code: int = 200
    headers: Dict[str, str] = field(default_factory=dict)
    links: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.error is not None or self.status_code >= 400

    def to_dict(self) -> Dict[str, Any]:
        return {
            "url": self.url,
            "content_type": self.content_type.value,
            "text": self.text,
            "title": self.title,
            "status_code": self.status_code,
            "headers": self.headers,
            "links": self.links,
            "error": self.error,
        }


# =============================================================================
# MONITOR SESSION
# =============================================================================


class MonitorSession:
    """
    A session for interacting with the monitor.

    Provides both synchronous and asynchronous methods for:
    - Fetching and rendering content
    - Running the full browser
    - Monitoring URLs for changes
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self._process: Optional[subprocess.Popen] = None
        self._callbacks: Dict[str, List[Callable]] = {}

    @property
    def is_available(self) -> bool:
        """Check if monitor is available."""
        return MONITOR_AVAILABLE

    def launch_browser(self, url: Optional[str] = None) -> int:
        """
        Launch the full browser interface.

        Args:
            url: Optional URL to open

        Returns:
            Exit code from the browser
        """
        if not MONITOR_AVAILABLE:
            raise RuntimeError(
                "Monitor binary not found. Install Chawan or build from tools_tui/monitor"
            )

        cmd = [CHAWAN_BINARY]
        cmd.extend(self.config.to_args())

        if url:
            cmd.append(url)

        result = subprocess.run(cmd, shell=False)
        return result.returncode

    def dump_url(self, url: str) -> MonitorContent:
        """
        Fetch a URL and return its text content.

        Args:
            url: URL to fetch

        Returns:
            MonitorContent with the fetched content
        """
        if not MONITOR_AVAILABLE:
            return MonitorContent(
                url=url,
                content_type=ContentType.PLAIN,
                text="",
                error="Monitor binary not found",
            )

        try:
            cmd = [CHAWAN_BINARY, "-d"]
            cmd.extend(self.config.to_args())
            cmd.append(url)

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.config.timeout
            )

            return MonitorContent(
                url=url,
                content_type=ContentType.PLAIN,
                text=result.stdout,
                status_code=0 if result.returncode == 0 else 500,
                error=result.stderr if result.returncode != 0 else None,
            )

        except subprocess.TimeoutExpired:
            return MonitorContent(
                url=url,
                content_type=ContentType.PLAIN,
                text="",
                error=f"Request timed out after {self.config.timeout}s",
            )
        except Exception as e:
            return MonitorContent(
                url=url, content_type=ContentType.PLAIN, text="", error=str(e)
            )

    async def dump_url_async(self, url: str) -> MonitorContent:
        """
        Asynchronously fetch a URL and return its text content.

        Args:
            url: URL to fetch

        Returns:
            MonitorContent with the fetched content
        """
        import asyncio

        if not MONITOR_AVAILABLE:
            return MonitorContent(
                url=url,
                content_type=ContentType.PLAIN,
                text="",
                error="Monitor binary not found",
            )

        try:
            cmd = [CHAWAN_BINARY, "-d"]
            cmd.extend(self.config.to_args())
            cmd.append(url)

            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.config.timeout
            )

            return MonitorContent(
                url=url,
                content_type=ContentType.PLAIN,
                text=stdout.decode(),
                status_code=0 if proc.returncode == 0 else 500,
                error=stderr.decode() if proc.returncode != 0 else None,
            )

        except asyncio.TimeoutError:
            return MonitorContent(
                url=url,
                content_type=ContentType.PLAIN,
                text="",
                error=f"Request timed out after {self.config.timeout}s",
            )
        except Exception as e:
            return MonitorContent(
                url=url, content_type=ContentType.PLAIN, text="", error=str(e)
            )

    def render_html(self, html: str, width: int = 80) -> str:
        """
        Render HTML to text using the monitor.

        Args:
            html: HTML content to render
            width: Output width

        Returns:
            Rendered text
        """
        if not MONITOR_AVAILABLE:
            # Fallback: strip HTML tags
            import re

            return re.sub(r"<[^>]+>", "", html)

        try:
            # Write HTML to temp file
            import tempfile

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".html", delete=False
            ) as f:
                f.write(html)
                temp_path = f.name

            try:
                cmd = [
                    CHAWAN_BINARY,
                    "-d",
                    "-o",
                    f"display.columns = {width}",
                    f"file://{temp_path}",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return result.stdout
            finally:
                os.unlink(temp_path)

        except Exception:
            import re

            return re.sub(r"<[^>]+>", "", html)

    def render_markdown(self, md: str, width: int = 80) -> str:
        """
        Render Markdown to text.

        Args:
            md: Markdown content
            width: Output width

        Returns:
            Rendered text
        """
        if not MONITOR_AVAILABLE:
            return md  # Return as-is if no renderer

        try:
            import tempfile

            with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
                f.write(md)
                temp_path = f.name

            try:
                cmd = [
                    CHAWAN_BINARY,
                    "-d",
                    "-T",
                    "text/markdown",
                    "-o",
                    f"display.columns = {width}",
                    f"file://{temp_path}",
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                return result.stdout
            finally:
                os.unlink(temp_path)

        except Exception:
            return md


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def launch_monitor(
    url: Optional[str] = None, config: Optional[MonitorConfig] = None
) -> int:
    """
    Launch the monitor browser.

    Args:
        url: Optional URL to open
        config: Optional configuration

    Returns:
        Exit code
    """
    session = MonitorSession(config)
    return session.launch_browser(url)


def render_content(
    content: str, content_type: str = "text/html", width: int = 80
) -> str:
    """
    Render content to text.

    Args:
        content: Content to render
        content_type: MIME type of content
        width: Output width

    Returns:
        Rendered text
    """
    session = MonitorSession()

    if content_type == "text/html":
        return session.render_html(content, width)
    elif content_type == "text/markdown":
        return session.render_markdown(content, width)
    else:
        return content
