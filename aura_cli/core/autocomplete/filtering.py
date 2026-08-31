"""Autocomplete suggestion filtering.

Provides intelligent filtering to remove irrelevant suggestions and reduce noise.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, List, Optional

from aura_cli.core.autocomplete.generation import Suggestion
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class FilterStrategy(Enum):
    """Filtering strategy enum."""

    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"
    CUSTOM = "custom"


@dataclass
class FilterRule:
    """Filter rule (name, filter_func, priority)."""

    name: str
    filter_func: Callable[[Suggestion], bool]
    priority: int = 100


class SuggestionFilter:
    """Filters autocomplete suggestions by relevance and context."""

    def __init__(self, strategy: FilterStrategy = FilterStrategy.MODERATE):
        """Initialise the suggestion filter."""
        self.strategy = strategy
        self.rules: List[FilterRule] = []
        self.stats = get_stats()

        self._load_default_rules()

        logger.info(f"SuggestionFilter initialized (strategy: {strategy.value})")

    def filter(
        self, suggestions: List[Suggestion], context: Optional[str] = None
    ) -> List[Suggestion]:
        """Filter suggestions for the given context."""
        if not suggestions:
            return []

        filtered = suggestions.copy()

        for rule in sorted(self.rules, key=lambda r: r.priority):
            filtered = [s for s in filtered if rule.filter_func(s)]

        if self.strategy == FilterStrategy.STRICT:
            filtered = self._filter_strict(filtered)
        elif self.strategy == FilterStrategy.MODERATE:
            filtered = self._filter_moderate(filtered)
        elif self.strategy == FilterStrategy.LENIENT:
            filtered = self._filter_lenient(filtered)

        logger.debug(f"Sugestões filtradas: {len(suggestions)} -> {len(filtered)}")

        self.stats.track_tool_usage("suggestion_filtering")

        return filtered

    def _filter_strict(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Filtragem estrita."""
        filtered = [s for s in suggestions if s.score >= 0.7]

        seen = set()
        unique = []
        for sug in filtered:
            if sug.completion not in seen:
                seen.add(sug.completion)
                unique.append(sug)

        return unique

    def _filter_moderate(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Filtragem moderada."""
        filtered = [s for s in suggestions if s.score >= 0.5]

        seen = set()
        unique = []
        for sug in filtered:
            if sug.completion not in seen:
                seen.add(sug.completion)
                unique.append(sug)

        return unique

    def _filter_lenient(self, suggestions: List[Suggestion]) -> List[Suggestion]:
        """Filtragem leniente."""
        seen = set()
        unique = []
        for sug in suggestions:
            if sug.completion not in seen:
                seen.add(sug.completion)
                unique.append(sug)

        return unique

    def add_rule(self, rule: FilterRule) -> None:
        """
        Adiciona regra de filtro.

        Args:
            rule: Regra a adicionar
        """
        self.rules.append(rule)
        logger.debug(f"Regra de filtro '{rule.name}' adicionada")

    def _load_default_rules(self) -> None:
        """Load the default filter rules."""
        empty_rule = FilterRule(
            name="remove_empty",
            filter_func=lambda s: bool(s.completion.strip()),
            priority=1,
        )
        self.rules.append(empty_rule)

        short_rule = FilterRule(
            name="remove_short",
            filter_func=lambda s: len(s.completion) >= 2,
            priority=2,
        )
        self.rules.append(short_rule)

        invalid_rule = FilterRule(
            name="remove_invalid",
            filter_func=lambda s: (
                s.completion.replace("_", "").replace(".", "").isalnum()
                or "_" in s.completion
                or "." in s.completion
            ),
            priority=3,
        )
        self.rules.append(invalid_rule)
