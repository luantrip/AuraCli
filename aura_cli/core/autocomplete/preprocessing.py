"""Context pre-processing for Autocomplete.

Provides context cleaning and optimisation before suggestion generation.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class PreprocessingRule(Enum):
    """Pre-processing rule definitions."""

    REMOVE_COMMENTS = "remove_comments"
    REMOVE_WHITESPACE = "remove_whitespace"
    REMOVE_IMPORTS = "remove_imports"
    REMOVE_DOCSTRINGS = "remove_docstrings"
    NORMALIZE_INDENTATION = "normalize_indentation"
    REMOVE_EMPTY_LINES = "remove_empty_lines"
    EXTRACT_KEYWORDS = "extract_keywords"
    REMOVE_NOISE = "remove_noise"


@dataclass
class ContextCleaner:
    """Context cleaner (rules, max_length, preserve_structure)."""

    rules: List[PreprocessingRule] = field(default_factory=list)
    max_length: int = 5000
    preserve_structure: bool = True


class ContextPreprocessor:
    """Context pre-processor for autocomplete."""

    def __init__(self):
        """Initialise the context pre-processor."""
        self.stats = get_stats()

        logger.info("ContextPreprocessor initialized")

    def preprocess(
        self,
        context: str,
        rules: Optional[List[PreprocessingRule]] = None,
        max_length: int = 5000,
    ) -> str:
        """Pre-process context before autocomplete generation."""
        if not context:
            return ""

        processed = context

        if rules is None:
            rules = [
                PreprocessingRule.REMOVE_NOISE,
                PreprocessingRule.REMOVE_EMPTY_LINES,
                PreprocessingRule.NORMALIZE_INDENTATION,
                PreprocessingRule.EXTRACT_KEYWORDS,
            ]

        for rule in rules:
            processed = self._apply_rule(processed, rule)

        if len(processed) > max_length:
            half = max_length // 2
            processed = processed[:half] + "\n...\n" + processed[-half:]

        logger.debug(
            f"Contexto pré-processado: {len(context)} -> {len(processed)} chars"
        )

        return processed

    def _apply_rule(self, context: str, rule: "PreprocessingRule") -> str:
        """Apply a preprocessing rule to context."""
        handlers = {
            PreprocessingRule.REMOVE_COMMENTS: self._rule_remove_comments,
            PreprocessingRule.REMOVE_WHITESPACE: self._rule_remove_whitespace,
            PreprocessingRule.REMOVE_IMPORTS: self._rule_remove_imports,
            PreprocessingRule.REMOVE_DOCSTRINGS: self._rule_remove_docstrings,
            PreprocessingRule.NORMALIZE_INDENTATION: self._rule_normalize_indentation,
            PreprocessingRule.REMOVE_EMPTY_LINES: self._rule_remove_empty_lines,
            PreprocessingRule.EXTRACT_KEYWORDS: self._rule_extract_keywords,
            PreprocessingRule.REMOVE_NOISE: self._rule_remove_noise,
        }
        handler = handlers.get(rule)
        return handler(context) if handler else context

    def _rule_remove_comments(self, ctx: str) -> str:
        ctx = re.sub(r"#.*$", "", ctx, flags=re.MULTILINE)
        ctx = re.sub(r'""".*?"""', "", ctx, flags=re.DOTALL)
        return re.sub(r"'''.*?'''", "", ctx, flags=re.DOTALL)

    def _rule_remove_whitespace(self, ctx: str) -> str:
        return "\n".join(" ".join(line.split()) for line in ctx.split("\n"))

    def _rule_remove_imports(self, ctx: str) -> str:
        return re.sub(r"^(import|from)\s+.*$", "", ctx, flags=re.MULTILINE)

    def _rule_remove_docstrings(self, ctx: str) -> str:
        ctx = re.sub(r'""".*?"""', "", ctx, flags=re.DOTALL)
        return re.sub(r"'''.*?'''", "", ctx, flags=re.DOTALL)

    def _rule_normalize_indentation(self, ctx: str) -> str:
        return "\n".join(line.rstrip() for line in ctx.split("\n"))

    def _rule_remove_empty_lines(self, ctx: str) -> str:
        result, prev_empty = [], False
        for line in ctx.split("\n"):
            is_empty = not line.strip()
            if not (is_empty and prev_empty):
                result.append(line)
            prev_empty = is_empty
        return "\n".join(result)

    def _rule_extract_keywords(self, ctx: str) -> str:
        _KW = {
            "def",
            "class",
            "if",
            "for",
            "while",
            "return",
            "yield",
            "async",
            "await",
        }
        relevant = [
            line
            for line in ctx.split("\n")
            if any(kw in line for kw in _KW)
            or line.strip().startswith(("def ", "class "))
        ]
        return "\n".join(relevant) if relevant else ctx

    def _rule_remove_noise(self, ctx: str) -> str:
        _BRACKETS = {"{", "}", "[", "]", "(", ")"}
        return "\n".join(
            line
            for line in ctx.split("\n")
            if len(line.strip()) > 2 or line.strip() in _BRACKETS
        )

    def extract_relevant_context(
        self, context: str, cursor_position: int, window_size: int = 200
    ) -> str:
        """Extract context relevant to the cursor position."""
        if not context:
            return ""

        start = max(0, cursor_position - window_size // 2)
        end = min(len(context), cursor_position + window_size // 2)

        if start > 0:
            while start > 0 and context[start] != "\n":
                start -= 1
            if start > 0:
                start += 1

        if end < len(context):
            while end < len(context) and context[end] != "\n":
                end += 1

        relevant = context[start:end]

        logger.debug(
            f"Contexto relevante extraído: {len(relevant)} chars ao redor da posição {cursor_position}"
        )

        return relevant

    def reduce_context_pollution(self, context: str, max_tokens: int = 1000) -> str:
        """Reduce context pollution to fit within a token budget."""
        cleaner = ContextCleaner(
            rules=[
                PreprocessingRule.REMOVE_COMMENTS,
                PreprocessingRule.REMOVE_DOCSTRINGS,
                PreprocessingRule.REMOVE_EMPTY_LINES,
                PreprocessingRule.REMOVE_NOISE,
                PreprocessingRule.EXTRACT_KEYWORDS,
            ],
            max_length=max_tokens * 4,
        )

        processed = self.preprocess(context, cleaner.rules, cleaner.max_length)

        if len(processed) > max_tokens * 4:
            lines = processed.split("\n")
            structure = []
            for line in lines:
                if line.strip().startswith(("def ", "class ")):
                    structure.append(line)
            processed = "\n".join(structure[: max_tokens // 10])

        logger.info(f"Poluição reduzida: {len(context)} -> {len(processed)} chars")

        self.stats.track_tool_usage("context_preprocessing")

        return processed
