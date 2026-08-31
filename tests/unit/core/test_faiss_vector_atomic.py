"""Atomic FAISS persistence contracts using a local fake backend."""

import json
from pathlib import Path
import threading

from aura_cli.core.memory.vector_store import FAISSVectorStore


class FakeFaiss:
    def write_index(self, _index, path: str) -> None:
        Path(path).write_bytes(b"fake-index")

    def read_index(self, path: str):
        assert Path(path).read_bytes() == b"fake-index"
        return "loaded-index"


def make_store(tmp_path):
    store = FAISSVectorStore.__new__(FAISSVectorStore)
    store._collection_name = "memory"
    store._persist_path = tmp_path
    store._faiss = FakeFaiss()
    store._index = "index"
    store._id_map = ["doc-1"]
    store._documents = {"doc-1": {"content": "hello", "metadata": {}}}
    store._lock = threading.RLock()
    return store


def test_faiss_save_publishes_verified_generation(tmp_path):
    store = make_store(tmp_path)

    store._save()

    manifest_path = tmp_path / "memory.manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    index_path = tmp_path / manifest["index"]
    metadata_path = tmp_path / manifest["metadata"]
    assert manifest["format_version"] == 1
    assert index_path.read_bytes() == b"fake-index"
    assert json.loads(metadata_path.read_text(encoding="utf-8"))["id_map"] == ["doc-1"]
    assert not list(tmp_path.glob("*.tmp"))


def test_faiss_load_rejects_tampered_generation(tmp_path):
    store = make_store(tmp_path)
    store._save()
    manifest = json.loads(
        (tmp_path / "memory.manifest.json").read_text(encoding="utf-8")
    )
    (tmp_path / manifest["metadata"]).write_text("{}", encoding="utf-8")

    restored = make_store(tmp_path)
    restored._id_map = []
    restored._documents = {}
    restored._load()

    assert restored._id_map == []
    assert restored._documents == {}
