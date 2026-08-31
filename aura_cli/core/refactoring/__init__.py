"""Refactoring package — intelligent, safe, semantic-aware refactoring.

Pipeline: plan_refactoring() → apply_refactoring_plan() with validation
and rollback. Semantic similarity via SemanticSimilarityAnalyzer detects
duplicate code opportunities. find_duplicate_code_semantic() is the main
entry point for duplication analysis.
"""

from aura_cli.core.refactoring.refactoring_executor import (
    RefactoringPlan,
    RefactoringSession,
    apply_change,
    apply_refactoring_plan,
    validate_change,
)
from aura_cli.core.refactoring.refactoring_planner import (
    analyze_impact_for_refactoring,
    plan_file_refactoring,
    plan_refactoring,
)
from aura_cli.core.refactoring.semantic_similarity import (
    CodeSimilarity,
    SemanticSimilarityAnalyzer,
    find_duplicate_code_semantic,
)

__all__ = [
    "CodeSimilarity",
    "RefactoringPlan",
    "RefactoringSession",
    "SemanticSimilarityAnalyzer",
    "analyze_impact_for_refactoring",
    "apply_change",
    "apply_refactoring_plan",
    "find_duplicate_code_semantic",
    "plan_file_refactoring",
    "plan_refactoring",
    "validate_change",
]
