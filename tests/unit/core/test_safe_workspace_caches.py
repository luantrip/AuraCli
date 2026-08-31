"""Safe serialization contracts for caches influenced by workspace files."""

import ast
import json
from pathlib import Path

import pytest

from aura_cli.core.context.code_index import CodebaseIndexer, CodeIndex
from aura_cli.core.embeddings import embeddings_advanced


def test_code_index_roundtrip_uses_versioned_json(tmp_path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("VALUE = 1\n", encoding="utf-8")
    indexer = CodebaseIndexer(scope=str(tmp_path))
    entry = CodeIndex(str(source))
    entry.constants = [{"name": "VALUE", "value": "1"}]
    indexer.file_indices[str(source)] = entry

    indexer._save_cache()

    assert indexer._cache_file.suffix == ".json"
    payload = json.loads(indexer._cache_file.read_text(encoding="utf-8"))
    assert payload["format_version"] == 1
    restored = CodebaseIndexer(scope=str(tmp_path))
    assert restored._load_cache() is True
    assert restored.file_indices[str(source)].constants == entry.constants


def test_legacy_pickle_is_never_considered_for_code_index(tmp_path) -> None:
    cache_dir = tmp_path / ".aura" / "index_cache"
    cache_dir.mkdir(parents=True)
    (cache_dir / "codebase_index.pkl").write_bytes(b"malicious pickle payload")

    indexer = CodebaseIndexer(scope=str(tmp_path))

    assert indexer._load_cache() is False


def test_embedding_index_roundtrip_uses_versioned_json(tmp_path, monkeypatch) -> None:
    """A persistência do índice não deve depender de fastembed ou de rede."""

    class FakeArray(list):
        def tolist(self):
            return list(self)

    class FakeNumpy:
        @staticmethod
        def array(values):
            return FakeArray(values)

    monkeypatch.setattr(embeddings_advanced, "np", FakeNumpy)

    index = embeddings_advanced.EmbeddingIndex.__new__(
        embeddings_advanced.EmbeddingIndex
    )
    index.model_name = "test-model"
    index.embedding_dim = 2
    index.embeddings = {"doc": FakeArray([0.25, 0.75])}
    index.metadata = {"doc": {"file_path": "sample.py"}}
    index._index_file = tmp_path / "embeddings_index.json"
    index._save_index()

    restored = embeddings_advanced.EmbeddingIndex.__new__(
        embeddings_advanced.EmbeddingIndex
    )
    restored.model_name = "test-model"
    restored.embeddings = {}
    restored.metadata = {}
    restored._index_file = index._index_file
    restored._load_index()

    assert restored.metadata == index.metadata
    assert restored.embeddings["doc"].tolist() == [0.25, 0.75]


def test_embedding_index_dependency_failure_is_explicit(monkeypatch) -> None:
    """A ausência do backend opcional é um contrato observável, não um skip."""
    monkeypatch.setattr(embeddings_advanced, "HAS_EMBEDDINGS", False)

    with pytest.raises(ImportError, match="fastembed"):
        embeddings_advanced.EmbeddingIndex()


def test_cache_modules_do_not_import_pickle() -> None:
    for filename in (
        "aura_cli/core/context/code_index.py",
        "aura_cli/core/embeddings/embeddings_advanced.py",
        "aura_cli/core/cache_advanced/persistent_cache.py",
    ):
        tree = ast.parse(Path(filename).read_text(encoding="utf-8"))
        imported = {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.Import)
            for alias in node.names
        }
        assert "pickle" not in imported
