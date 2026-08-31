"""
Autocomplete system for Aura CLI — optional /dashboard command widget.

Loaded lazily on demand;  demanda via ``importlib`` em
``cli/ui/composition/dashboard_surface.py`` when the user runs
``/dashboard autocomplete``. Not imported directly in newhere else
by design — it is an optional plugin of the dashoards.

Componentes:
    - AutocompleteWidget: Widget interativo de autocomplete
    - SnippetBrowser: Code snippet browser
    - TemplateEditor: Template editor of templates
    - SuggestionType: Suggestion type enum
    - Suggestion: Suggestion dataclass for suggestions
    - Snippet: Dataclass for snippets
    - Template: Dataclass para templates
"""

from aura_cli.cli.ui.autocomplete.autocomplete_widget import (
    AutocompleteWidget,
    Snippet,
    SnippetBrowser,
    Suggestion,
    SuggestionType,
    Template,
    TemplateEditor,
    show_autocomplete_dashboard,
)

__all__ = [
    "AutocompleteWidget",
    "Snippet",
    "SnippetBrowser",
    "Suggestion",
    "SuggestionType",
    "Template",
    "TemplateEditor",
    "show_autocomplete_dashboard",
]
