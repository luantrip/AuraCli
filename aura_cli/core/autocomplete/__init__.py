"""
Auxiliary autocomplete infrastructure for Aura CLI UX.

Bundles preprocessing, classification, generationo e filtering of
suggestions for completion flows and local assistance. Remains useful for
CLI/TUI and opt-in components, but is not a central semantic axis of the product.o.

O centro arquitetural da Aura CLI permanece em `context`, `memory`, `llm` e no
loop principal do chat. `core.autocomplete` deve ser trataas experience support usage, not as a canonical runtime subsystem.
"""

from aura_cli.core.autocomplete.classification import (
    ClassificationResult,
    ContextClassifier,
    ContextType,
)
from aura_cli.core.autocomplete.filtering import (
    FilterRule,
    FilterStrategy,
    SuggestionFilter,
)
from aura_cli.core.autocomplete.generation import (
    AutocompleteGenerator,
    GenerationStrategy,
    Suggestion,
)
from aura_cli.core.autocomplete.preprocessing import (
    ContextCleaner,
    ContextPreprocessor,
    PreprocessingRule,
)
from aura_cli.core.autocomplete.snippets import CodeSnippet, SnippetManager, SnippetType
from aura_cli.core.autocomplete.templating import (
    CodeTemplate,
    TemplateEngine,
    TemplateVariable,
)

__all__ = [
    "AutocompleteGenerator",
    "ClassificationResult",
    "CodeSnippet",
    "CodeTemplate",
    "ContextClassifier",
    "ContextCleaner",
    "ContextPreprocessor",
    "ContextType",
    "FilterRule",
    "FilterStrategy",
    "GenerationStrategy",
    "PreprocessingRule",
    "SnippetManager",
    "SnippetType",
    "Suggestion",
    "SuggestionFilter",
    "TemplateEngine",
    "TemplateVariable",
]
