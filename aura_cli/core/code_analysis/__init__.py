"""Auxiliary code-analysis library for tooling and context support.

Provides CodeTokenizer (structure-preserving Python tokenisation) and
NLPAnalyzer (classification, summarisation, complexity, feature extraction)
used by dev_tools and context builders. Not a first-class runtime domain.
"""

from aura_cli.core.code_analysis.nlp_analyzer import (
    CodeClassification,
    CodeSummary,
    ComplexityLevel,
    NLPAnalyzer,
)
from aura_cli.core.code_analysis.tokenizer import CodeTokenizer, TokenizationResult

__all__ = [
    "CodeClassification",
    "CodeSummary",
    "CodeTokenizer",
    "ComplexityLevel",
    "NLPAnalyzer",
    "TokenizationResult",
]
