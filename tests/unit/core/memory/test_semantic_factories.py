"""Semantic infrastructure factories must not hide shared mutable state."""

from aura_cli.core.memory_advanced.cognitive_refinement import get_cognitive_refinement
from aura_cli.core.memory_advanced.embeddings import EmbeddingModel, get_embedding_model
from aura_cli.core.memory_advanced.vector_storage import VectorStorage


def test_refinement_factory_respects_explicit_storage() -> None:
    storage = VectorStorage()
    assert get_cognitive_refinement(storage).storage is storage


def test_semantic_factories_create_independent_instances() -> None:
    first_refinement = get_cognitive_refinement(VectorStorage())
    second_refinement = get_cognitive_refinement(VectorStorage())
    first_embedding = get_embedding_model(EmbeddingModel.SIMPLE, 8)
    second_embedding = get_embedding_model(EmbeddingModel.SIMPLE, 8)

    assert first_refinement is not second_refinement
    assert first_embedding is not second_embedding
