"""Atomic persistence contracts for the keyword vector-store fallback."""

from concurrent.futures import ThreadPoolExecutor
import json
from unittest.mock import patch

import pytest

from aura_cli.core.memory.vector_store import KeywordVectorStore


def test_keyword_store_persists_json_without_temporary_file(tmp_path):
    store = KeywordVectorStore(collection_name="memory", persist_path=str(tmp_path))

    store.add("new document", doc_id="doc-1")

    path = tmp_path / "memory.json"
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["doc-1"]["content"] == "new document"
    assert not list(tmp_path.glob(f".{path.name}.*.tmp"))


def test_keyword_store_keeps_previous_json_when_replace_fails(tmp_path):
    store = KeywordVectorStore(collection_name="memory", persist_path=str(tmp_path))
    path = tmp_path / "memory.json"
    previous = '{"old": {"content": "old"}}'
    path.write_text(previous, encoding="utf-8")
    store._documents = {"new": {"content": "new", "metadata": {}}}

    with patch(
        "aura_cli.core.memory.vector_store.os.replace",
        side_effect=OSError("replace failed"),
    ):
        with pytest.raises(OSError, match="replace failed"):
            store._save()

    assert path.read_text(encoding="utf-8") == previous
    assert not list(tmp_path.glob(f".{path.name}.*.tmp"))


def test_keyword_store_serializes_concurrent_mutations(tmp_path):
    store = KeywordVectorStore(collection_name="memory", persist_path=str(tmp_path))

    def add_document(index):
        return store.add(f"document {index}", doc_id=f"doc-{index}")

    with ThreadPoolExecutor(max_workers=4) as executor:
        ids = list(executor.map(add_document, range(12)))

    assert len(ids) == 12
    assert store.count() == 12
    saved = json.loads((tmp_path / "memory.json").read_text(encoding="utf-8"))
    assert len(saved) == 12
