"""
Markdown snippets system for quick text expansion.

Provides built-in and customizable snippets for markdown editing.
"""

import json
import logging
from typing import ClassVar, Dict, NamedTuple, Optional

from aura_cli.core.paths import get_aura_home

logger = logging.getLogger(__name__)

CONFIG_DIR = get_aura_home()
SNIPPETS_FILE = CONFIG_DIR / "snippets.json"


class SnippetInfo(NamedTuple):
    """Snippet definition."""

    content: str
    description: str


class SnippetManager:
    """
    Manages markdown snippet expansion.

    Provides built-in snippets and supports user-defined custom snippets
    loaded from JSON configuration.
    """

    BUILTIN_SNIPPETS: ClassVar[Dict[str, SnippetInfo]] = {
        "h1": SnippetInfo("# ", "Level 1 heading"),
        "h2": SnippetInfo("## ", "Level 2 heading"),
        "h3": SnippetInfo("### ", "Level 3 heading"),
        "h4": SnippetInfo("#### ", "Level 4 heading"),
        "bold": SnippetInfo("****", "Bold text"),
        "italic": SnippetInfo("**", "Italic text"),
        "strike": SnippetInfo("~~~~", "Strikethrough text"),
        "code": SnippetInfo("``", "Inline code"),
        "codeblock": SnippetInfo("```\n\n```", "Code block"),
        "codepy": SnippetInfo("```python\n\n```", "Python code block"),
        "codejs": SnippetInfo("```javascript\n\n```", "JavaScript code block"),
        "codesh": SnippetInfo("```bash\n\n```", "Shell code block"),
        "ul": SnippetInfo("- ", "Unordered list item"),
        "ol": SnippetInfo("1. ", "Ordered list item"),
        "link": SnippetInfo("[]()", "Markdown link"),
        "img": SnippetInfo("![]()", "Image"),
        "quote": SnippetInfo("> ", "Blockquote"),
        "hr": SnippetInfo("---", "Horizontal rule"),
        "todo": SnippetInfo("- [ ] ", "Todo item"),
        "done": SnippetInfo("- [x] ", "Completed todo item"),
        "table": SnippetInfo(
            "| Column 1 | Column 2 |\n|----------|----------|\n| Cell 1   | Cell 2   |",
            "Table",
        ),
        "details": SnippetInfo(
            "<details>\n<summary>Click to expand</summary>\n\n</details>",
            "Collapsible section",
        ),
    }

    def __init__(self):
        """Initialize the instance."""
        self._custom_snippets: Dict[str, SnippetInfo] = {}
        self._load_custom_snippets()

    def _load_custom_snippets(self) -> None:
        """Load custom snippets from JSON config file."""
        try:
            if SNIPPETS_FILE.exists():
                data = json.loads(SNIPPETS_FILE.read_text(encoding="utf-8"))
                self._custom_snippets = {
                    k: SnippetInfo(v["content"], v.get("description", "Custom snippet"))
                    for k, v in data.items()
                }
                logger.debug(f"Loaded {len(self._custom_snippets)} custom snippets")
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.warning(f"Error loading custom snippets: {e}")

    def save_custom_snippets(self) -> None:
        """Save custom snippets to JSON config file."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            data = {
                k: {"content": v.content, "description": v.description}
                for k, v in self._custom_snippets.items()
            }
            SNIPPETS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError as e:
            logger.error(f"Error saving custom snippets: {e}")

    def get_snippet(self, trigger: str) -> Optional[SnippetInfo]:
        """Get snippet info for a trigger."""
        return self._custom_snippets.get(trigger) or self.BUILTIN_SNIPPETS.get(trigger)

    def expand(self, trigger: str) -> Optional[str]:
        """
        Expand a snippet trigger into its content.

        Args:
            trigger: The snippet trigger text

        Returns:
            Expanded snippet content or None if no match
        """
        info = self.get_snippet(trigger)
        return info.content if info else None

    def add_custom(self, trigger: str, content: str, description: str = "") -> None:
        """Add or update a custom snippet."""
        self._custom_snippets[trigger] = SnippetInfo(
            content, description or "Custom snippet"
        )
        self.save_custom_snippets()

    def remove_custom(self, trigger: str) -> bool:
        """Remove a custom snippet."""
        if trigger in self._custom_snippets:
            del self._custom_snippets[trigger]
            self.save_custom_snippets()
            return True
        return False

    def list_all(self) -> Dict[str, SnippetInfo]:
        """Get all available snippets (built-in + custom)."""
        return {**self.BUILTIN_SNIPPETS, **self._custom_snippets}

    def list_builtin(self) -> Dict[str, SnippetInfo]:
        """Get built-in snippets."""
        return self.BUILTIN_SNIPPETS.copy()

    def list_custom(self) -> Dict[str, SnippetInfo]:
        """Get custom snippets."""
        return self._custom_snippets.copy()

    def search(self, query: str) -> Dict[str, SnippetInfo]:
        """Search snippets by trigger or description."""
        query = query.lower()
        results = {}
        for trigger, info in self.list_all().items():
            if query in trigger.lower() or query in info.description.lower():
                results[trigger] = info
        return results


_manager: Optional[SnippetManager] = None


def get_snippet_manager() -> SnippetManager:
    """Get global SnippetManager instance."""
    global _manager
    if _manager is None:
        _manager = SnippetManager()
    return _manager
