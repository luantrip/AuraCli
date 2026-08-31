"""Tests for explicit model-selection policies in helper workflows."""

from aura_cli.core.context.project_indexer import PROJECT_INDEXER_DEFAULT_MODEL
from aura_cli.core.llm.model_utils import DEFAULT_GEMINI_MODEL
from aura_cli.core.memory.cognitive_refiner import COGNITIVE_REFINER_MODEL


def test_project_indexer_uses_explicit_fast_model_policy():
    """Project indexing should use an explicit quick-analysis model policy."""
    assert PROJECT_INDEXER_DEFAULT_MODEL == DEFAULT_GEMINI_MODEL


def test_cognitive_refiner_uses_explicit_fast_model_policy():
    """Memory refinement should use an explicit quick-analysis model policy."""
    assert COGNITIVE_REFINER_MODEL == DEFAULT_GEMINI_MODEL
