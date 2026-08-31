"""Context classification for Autocomplete.

Provides intelligent context classification for type and relevance determination.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class ContextType(Enum):
    """Tipos de contexto."""

    FUNCTION_DEFINITION = "function_definition"
    CLASS_DEFINITION = "class_definition"
    METHOD_CALL = "method_call"
    VARIABLE_ASSIGNMENT = "variable_assignment"
    IMPORT_STATEMENT = "import_statement"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    RETURN_STATEMENT = "return_statement"
    DOCSTRING = "docstring"
    COMMENT = "comment"
    UNKNOWN = "unknown"


@dataclass
class ClassificationResult:
    """Result of a context classification."""

    context_type: ContextType
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    relevant_keywords: List[str] = field(default_factory=list)


class ContextClassifier:
    """Classifies code context for autocomplete routing."""

    def __init__(self):
        """Initialise the context classifier."""
        self.stats = get_stats()

        self.patterns = {
            ContextType.FUNCTION_DEFINITION: [
                r"^\s*def\s+\w+\s*\(",
                r"^\s*async\s+def\s+\w+\s*\(",
            ],
            ContextType.CLASS_DEFINITION: [
                r"^\s*class\s+\w+",
            ],
            ContextType.METHOD_CALL: [r"\w+\.\w+\s*\(", r"\w+\s*\("],
            ContextType.VARIABLE_ASSIGNMENT: [r"^\s*\w+\s*=", r"^\s*\w+\s*:.*="],
            ContextType.IMPORT_STATEMENT: [
                r"^\s*(import|from)\s+",
            ],
            ContextType.CONDITIONAL: [r"^\s*if\s+", r"^\s*elif\s+", r"^\s*else\s*:"],
            ContextType.LOOP: [r"^\s*for\s+", r"^\s*while\s+"],
            ContextType.RETURN_STATEMENT: [r"^\s*return\s+", r"^\s*yield\s+"],
            ContextType.DOCSTRING: [r'""".*?"""', r"'''.*?'''"],
            ContextType.COMMENT: [
                r"^\s*#",
            ],
        }

        logger.info("ContextClassifier initialized")

    def classify(
        self, context: str, cursor_position: Optional[int] = None
    ) -> ClassificationResult:
        """Classify the given context."""
        if not context:
            return ClassificationResult(
                context_type=ContextType.UNKNOWN, confidence=0.0
            )

        if cursor_position is not None:
            lines = context[:cursor_position].split("\n")
            current_line = lines[-1] if lines else ""
        else:
            lines = context.split("\n")
            current_line = lines[-1] if lines else ""

        best_match = None
        best_confidence = 0.0
        matched_type = ContextType.UNKNOWN

        for context_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, current_line, re.MULTILINE):
                    confidence = 0.8
                    if context_type in [
                        ContextType.FUNCTION_DEFINITION,
                        ContextType.CLASS_DEFINITION,
                    ]:
                        confidence = 0.95

                    if confidence > best_confidence:
                        best_confidence = confidence
                        matched_type = context_type
                        best_match = pattern

        keywords = self._extract_keywords(context)

        metadata = {
            "line": current_line.strip(),
            "line_number": len(lines),
            "pattern": best_match,
        }

        result = ClassificationResult(
            context_type=matched_type,
            confidence=best_confidence,
            metadata=metadata,
            relevant_keywords=keywords,
        )

        logger.debug(
            f"Contexto classificado como: {matched_type.value} (confiança: {best_confidence:.2f})"
        )

        self.stats.track_tool_usage("context_classification")

        return result

    def _extract_keywords(self, context: str) -> List[str]:
        """Extract keywords from a context string."""
        keywords = []

        python_keywords = [
            "def",
            "class",
            "if",
            "else",
            "elif",
            "for",
            "while",
            "return",
            "yield",
            "async",
            "await",
            "import",
            "from",
            "try",
            "except",
            "finally",
            "with",
            "as",
            "pass",
            "break",
            "continue",
        ]

        var_pattern = r"\b([a-z_][a-z0-9_]*)\s*="
        func_pattern = r"\bdef\s+([a-z_][a-z0-9_]*)"
        class_pattern = r"\bclass\s+([A-Z][a-zA-Z0-9_]*)"

        for pattern in [var_pattern, func_pattern, class_pattern]:
            matches = re.findall(pattern, context)
            keywords.extend(matches)

        keywords = list(set(keywords))
        keywords = [kw for kw in keywords if kw not in python_keywords]

        return keywords[:10]

    def classify_multiple(self, contexts: List[str]) -> List[ClassificationResult]:
        """Classify multiple contexts."""
        return [self.classify(ctx) for ctx in contexts]
