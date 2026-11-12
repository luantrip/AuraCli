"""Honest embedding fallback and collapsed semantic shim contracts.

- The phantom OPENAI mode (never implemented, silently returned the hash) is gone.
- The SIMPLE fallback announces that it is non-semantic instead of pretending.
- semantic/embeddings.py shim removed; the canonical module is memory_advanced.
"""

from __future__ import annotations

import importlib.util

import numpy as np

from aura_cli.core.memory.embeddings import EmbeddingGenerator, EmbeddingModel


class TestNoPhantomOpenAIMode:
    def test_openai_mode_is_removed(self) -> None:
        assert "OPENAI" not in EmbeddingModel.__members__

    def test_only_documented_modes_exist(self) -> None:
        assert set(EmbeddingModel.__members__) == {
            "FASTEMBED",
            "HUGGINGFACE",
            "CODEBERT",
            "CODEBERTA",
            "SIMPLE",
        }


class TestHonestFallback:
    def test_simple_fallback_warns_that_it_is_not_semantic(self, caplog) -> None:
        gen = EmbeddingGenerator(model=EmbeddingModel.SIMPLE, dimension=384)
        with caplog.at_level("WARNING"):
            gen._warn_semantic_unavailable("fastembed is not installed")
        text = caplog.text.lower()
        assert "not" in text and "semantic" in text
        assert "fastembed" in text  # points to the fix

    def test_simple_embedding_still_returns_a_normalized_vector(self) -> None:
        gen = EmbeddingGenerator(model=EmbeddingModel.SIMPLE, dimension=384)
        vector = gen._simple_embedding("hello world")
        assert vector.shape == (384,)
        # Unit-normalized (so downstream cosine math does not blow up), even though
        # the direction carries no semantic meaning.
        assert np.isclose(np.linalg.norm(vector), 1.0, atol=1e-6)


class TestShimCollapsed:
    def test_semantic_embeddings_shim_module_is_gone(self) -> None:
        assert importlib.util.find_spec("aura_cli.core.semantic.embeddings") is None

    def test_semantic_package_still_reexports_the_canonical_symbols(self) -> None:
        from aura_cli.core.memory.embeddings import EmbeddingGenerator as CG
        from aura_cli.core.memory.embeddings import EmbeddingModel as CM
        from aura_cli.core.semantic import EmbeddingGenerator as G
        from aura_cli.core.semantic import EmbeddingModel as M

        assert G is CG
        assert M is CM
