"""Snippet manager for Autocomplete.

Provides code snippet management for autocomplete suggestions.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class SnippetType(Enum):
    """Tipos de snippet."""

    FUNCTION = "function"
    CLASS = "class"
    LOOP = "loop"
    CONDITIONAL = "conditional"
    IMPORT = "import"
    DECORATOR = "decorator"
    CONTEXT_MANAGER = "context_manager"
    CUSTOM = "custom"


@dataclass
class CodeSnippet:
    """A reusable code snippet with metadata."""

    snippet_id: str
    name: str
    snippet_type: SnippetType
    code: str
    description: str = ""
    tags: List[str] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)


class SnippetManager:
    """Manages a library of reusable code snippets."""

    def __init__(self):
        """Initialise the snippet manager."""
        self.snippets: Dict[str, CodeSnippet] = {}
        self.stats = get_stats()

        self._load_default_snippets()

        logger.info("SnippetManager initialized")

    def add_snippet(
        self,
        name: str,
        snippet_type: SnippetType,
        code: str,
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> CodeSnippet:
        """Add a snippet to the library."""
        import uuid

        snippet = CodeSnippet(
            snippet_id=str(uuid.uuid4())[:8],
            name=name,
            snippet_type=snippet_type,
            code=code,
            description=description,
            tags=tags or [],
        )

        self.snippets[snippet.snippet_id] = snippet

        logger.debug(f"Snippet '{name}' adicionado")

        return snippet

    def search_snippets(
        self,
        query: str = "",
        snippet_type: Optional[SnippetType] = None,
        tags: Optional[List[str]] = None,
    ) -> List[CodeSnippet]:
        """Search snippets by query, type and tags."""
        results = list(self.snippets.values())

        if snippet_type:
            results = [s for s in results if s.snippet_type == snippet_type]

        if tags:
            results = [s for s in results if any(tag in s.tags for tag in tags)]

        if query:
            query_lower = query.lower()
            results = [
                s
                for s in results
                if query_lower in s.name.lower()
                or query_lower in s.description.lower()
                or any(query_lower in tag.lower() for tag in s.tags)
            ]

        return results

    def expand_snippet(
        self, snippet: CodeSnippet, variables: Optional[Dict[str, str]] = None
    ) -> str:
        """Expand a snippet with the given variable values."""
        code = snippet.code
        variables = variables or {}

        for var_name, var_value in variables.items():
            code = code.replace(f"${var_name}", var_value)
            code = code.replace(f"{{{var_name}}}", var_value)

        return code

    def _load_default_snippets(self) -> None:
        """Load the built-in default snippets."""
        self.add_snippet(
            "function",
            SnippetType.FUNCTION,
            "def ${name}(${params}):\n    ${body}",
            "Function definition",
            ["function", "def"],
        )

        self.add_snippet(
            "class",
            SnippetType.CLASS,
            "class ${name}(${base}):\n    ${body}",
            "Class definition",
            ["class"],
        )

        self.add_snippet(
            "for_loop",
            SnippetType.LOOP,
            "for ${item} in ${iterable}:\n    ${body}",
            "For loop",
            ["loop", "for", "iteration"],
        )

        self.add_snippet(
            "if_statement",
            SnippetType.CONDITIONAL,
            "if ${condition}:\n    ${body}",
            "If statement",
            ["conditional", "if"],
        )

        self.add_snippet(
            "try_except",
            SnippetType.CONDITIONAL,
            "try:\n    ${body}\nexcept ${exception} as ${error}:\n    ${handler}",
            "Try-except block",
            ["error", "exception", "try"],
        )
