"""Monitor browser interface.

High-level browser interface for Monitor Tool.

Features:
    - Async web content fetching
    - Content rendering and display
    - Tab management
    - Navigation history
    - Search functionality
    - Browser state management
    - URL parsing and validation

Classes:
    NavigationAction: Browser navigation actions enum
    BrowserTab: Individual browser tab representation
    BrowserState: Complete browser state manager
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from typing import Callable, List, Optional, Tuple
from urllib.parse import urljoin

from aura_cli.application.presentation.monitor import normalize_monitor_url
from aura_cli.tui.tools.monitor import (
    ContentType,
    MonitorConfig,
    MonitorSession,
    get_monitor_binary,
)

# =============================================================================
# BROWSER STATE
# =============================================================================


class NavigationAction(Enum):
    """Browser navigation actions."""

    GOTO = "goto"
    BACK = "back"
    FORWARD = "forward"
    RELOAD = "reload"
    HOME = "home"


@dataclass
class BrowserTab:
    """Represents a browser tab."""

    id: int
    url: str
    title: str = ""
    content: str = ""
    content_type: ContentType = ContentType.HTML
    scroll_position: int = 0
    history: List[str] = field(default_factory=list)
    history_index: int = -1
    loading: bool = False
    error: Optional[str] = None
    last_updated: Optional[datetime] = None

    def can_go_back(self) -> bool:
        return self.history_index > 0

    def can_go_forward(self) -> bool:
        return self.history_index < len(self.history) - 1


@dataclass
class BrowserState:
    """Complete browser state."""

    tabs: List[BrowserTab] = field(default_factory=list)
    active_tab_index: int = 0
    status_message: str = ""
    input_mode: bool = False
    input_prompt: str = ""
    input_value: str = ""
    search_query: str = ""
    search_results: List[int] = field(default_factory=list)
    current_search_index: int = 0

    @property
    def active_tab(self) -> Optional[BrowserTab]:
        if 0 <= self.active_tab_index < len(self.tabs):
            return self.tabs[self.active_tab_index]
        return None

    def add_tab(self, url: str = "about:blank") -> BrowserTab:
        tab_id = max((t.id for t in self.tabs), default=0) + 1
        tab = BrowserTab(id=tab_id, url=url)
        self.tabs.append(tab)
        self.active_tab_index = len(self.tabs) - 1
        return tab

    def close_tab(self, index: Optional[int] = None) -> bool:
        if len(self.tabs) <= 1:
            return False

        idx = index if index is not None else self.active_tab_index
        if 0 <= idx < len(self.tabs):
            self.tabs.pop(idx)
            if self.active_tab_index >= len(self.tabs):
                self.active_tab_index = len(self.tabs) - 1
            return True
        return False


# =============================================================================
# BROWSER CLASS
# =============================================================================


class MonitorBrowser:
    """
    High-level browser interface.

    Features:
        - Tab management
        - Navigation history
        - Async content loading
        - Search within page
        - Bookmarks
    """

    def __init__(self, config: Optional[MonitorConfig] = None):
        self.config = config or MonitorConfig()
        self.session = MonitorSession(self.config)
        self.state = BrowserState()

        # Event callbacks
        self._on_navigate: List[Callable[[str], None]] = []
        self._on_content_loaded: List[Callable[[BrowserTab], None]] = []
        self._on_error: List[Callable[[str], None]] = []
        self._on_state_changed: List[Callable[[BrowserState], None]] = []

        # Create initial tab
        self.state.add_tab()

    @property
    def is_available(self) -> bool:
        return get_monitor_binary(refresh=True) is not None

    @property
    def current_tab(self) -> Optional[BrowserTab]:
        return self.state.active_tab

    @property
    def current_url(self) -> str:
        tab = self.current_tab
        return tab.url if tab else ""

    @property
    def current_content(self) -> str:
        tab = self.current_tab
        return tab.content if tab else ""

    # Event Handling

    def on_navigate(self, callback: Callable[[str], None]) -> None:
        """Register navigation callback."""
        self._on_navigate.append(callback)

    def on_content_loaded(self, callback: Callable[[BrowserTab], None]) -> None:
        """Register content loaded callback."""
        self._on_content_loaded.append(callback)

    def on_error(self, callback: Callable[[str], None]) -> None:
        """Register error callback."""
        self._on_error.append(callback)

    def on_state_changed(self, callback: Callable[[BrowserState], None]) -> None:
        """Register state change callback."""
        self._on_state_changed.append(callback)

    def _emit_navigate(self, url: str) -> None:
        for cb in self._on_navigate:
            cb(url)

    def _emit_content_loaded(self, tab: BrowserTab) -> None:
        for cb in self._on_content_loaded:
            cb(tab)

    def _emit_error(self, error: str) -> None:
        for cb in self._on_error:
            cb(error)

    def _emit_state_changed(self) -> None:
        for cb in self._on_state_changed:
            cb(self.state)

    # Navigation

    async def goto(self, url: str) -> bool:
        """
        Navigate to a URL.

        Args:
            url: URL to navigate to

        Returns:
            True if navigation succeeded
        """
        tab = self.current_tab
        if not tab:
            return False

        # Normalize URL
        url = normalize_monitor_url(url)

        tab.loading = True
        tab.error = None
        self.state.status_message = f"Loading {url}..."
        self._emit_navigate(url)
        self._emit_state_changed()

        try:
            content = await self.session.dump_url_async(url)

            if content.is_error:
                tab.error = content.error
                tab.content = f"Error loading {url}:\n{content.error}"
                self._emit_error(content.error or "Unknown error")
            else:
                tab.content = content.text
                tab.content_type = content.content_type

                # Update history
                if tab.url != url:
                    # Trim forward history
                    tab.history = tab.history[: tab.history_index + 1]
                    tab.history.append(url)
                    tab.history_index = len(tab.history) - 1

                tab.url = url
                tab.title = self._extract_title(content.text) or url
                tab.last_updated = datetime.now()

                self._emit_content_loaded(tab)

            tab.loading = False
            self.state.status_message = (
                tab.title if not tab.error else f"Error: {tab.error}"
            )
            self._emit_state_changed()

            return not content.is_error

        except Exception as e:
            tab.loading = False
            tab.error = str(e)
            self.state.status_message = f"Error: {e}"
            self._emit_error(str(e))
            self._emit_state_changed()
            return False

    async def go_back(self) -> bool:
        """Navigate back in history."""
        tab = self.current_tab
        if not tab or not tab.can_go_back():
            return False

        tab.history_index -= 1
        url = tab.history[tab.history_index]
        return await self.goto(url)

    async def go_forward(self) -> bool:
        """Navigate forward in history."""
        tab = self.current_tab
        if not tab or not tab.can_go_forward():
            return False

        tab.history_index += 1
        url = tab.history[tab.history_index]
        return await self.goto(url)

    async def reload(self) -> bool:
        """Reload current page."""
        tab = self.current_tab
        if not tab:
            return False
        return await self.goto(tab.url)

    # Content Operations

    def _extract_title(self, html: str) -> Optional[str]:
        """Extract title from HTML content."""
        match = re.search(r"<title[^>]*>([^<]+)</title>", html, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return None

    def search_in_page(self, query: str) -> List[int]:
        """
        Search for text in current page.

        Args:
            query: Search query

        Returns:
            List of line numbers with matches
        """
        tab = self.current_tab
        if not tab or not query:
            return []

        self.state.search_query = query
        self.state.search_results = []
        self.state.current_search_index = 0

        lines = tab.content.split("\n")
        for i, line in enumerate(lines):
            if query.lower() in line.lower():
                self.state.search_results.append(i)

        self._emit_state_changed()
        return self.state.search_results

    def next_search_result(self) -> Optional[int]:
        """Go to next search result."""
        if not self.state.search_results:
            return None

        self.state.current_search_index = (self.state.current_search_index + 1) % len(
            self.state.search_results
        )
        self._emit_state_changed()
        return self.state.search_results[self.state.current_search_index]

    def prev_search_result(self) -> Optional[int]:
        """Go to previous search result."""
        if not self.state.search_results:
            return None

        self.state.current_search_index = (self.state.current_search_index - 1) % len(
            self.state.search_results
        )
        self._emit_state_changed()
        return self.state.search_results[self.state.current_search_index]

    # Tab Management

    def new_tab(self, url: str = "about:blank") -> BrowserTab:
        """Create a new tab."""
        tab = self.state.add_tab(url)
        self._emit_state_changed()
        return tab

    def close_tab(self, index: Optional[int] = None) -> bool:
        """Close a tab."""
        result = self.state.close_tab(index)
        self._emit_state_changed()
        return result

    def switch_tab(self, index: int) -> bool:
        """Switch to a tab by index."""
        if 0 <= index < len(self.state.tabs):
            self.state.active_tab_index = index
            self._emit_state_changed()
            return True
        return False

    def next_tab(self) -> None:
        """Switch to next tab."""
        if self.state.tabs:
            self.state.active_tab_index = (self.state.active_tab_index + 1) % len(
                self.state.tabs
            )
            self._emit_state_changed()

    def prev_tab(self) -> None:
        """Switch to previous tab."""
        if self.state.tabs:
            self.state.active_tab_index = (self.state.active_tab_index - 1) % len(
                self.state.tabs
            )
            self._emit_state_changed()

    # Utility

    def get_links(self) -> List[Tuple[str, str]]:
        """
        Extract links from current page.

        Returns:
            List of (text, url) tuples
        """
        tab = self.current_tab
        if not tab:
            return []

        links = []
        # Simple regex for href extraction
        for match in re.finditer(
            r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]*)</a>',
            tab.content,
            re.IGNORECASE,
        ):
            url = match.group(1)
            text = match.group(2).strip() or url

            # Resolve relative URLs
            if not url.startswith(("http://", "https://", "file://")):
                url = urljoin(tab.url, url)

            links.append((text, url))

        return links

    def set_content(
        self, content: str, content_type: ContentType = ContentType.PLAIN
    ) -> None:
        """
        Set content directly without fetching.

        Args:
            content: Content to display
            content_type: Type of content
        """
        tab = self.current_tab
        if tab:
            tab.content = content
            tab.content_type = content_type
            tab.last_updated = datetime.now()
            self._emit_content_loaded(tab)
            self._emit_state_changed()
