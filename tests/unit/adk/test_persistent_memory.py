"""Unit tests for adk.memory — PersistentMemory."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from aura_cli.adk.memory import MemoryEntry, PersistentMemory

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def tmp_mem(tmp_path: Path) -> PersistentMemory:
    return PersistentMemory(tmp_path / "mem.jsonl")


# ---------------------------------------------------------------------------
# add / get
# ---------------------------------------------------------------------------


def test_add_returns_string_id(tmp_mem: PersistentMemory) -> None:
    entry_id = _run(tmp_mem.add("hello world"))
    assert isinstance(entry_id, str)
    assert len(entry_id) > 0


def test_get_returns_entry_after_add(tmp_mem: PersistentMemory) -> None:
    entry_id = _run(tmp_mem.add("test content", metadata={"tag": "unit"}))
    entry = _run(tmp_mem.get(entry_id))
    assert entry is not None
    assert entry.content == "test content"
    assert entry.metadata == {"tag": "unit"}


def test_get_unknown_id_returns_none(tmp_mem: PersistentMemory) -> None:
    result = _run(tmp_mem.get("__nonexistent__"))
    assert result is None


def test_add_multiple_unique_ids(tmp_mem: PersistentMemory) -> None:
    id1 = _run(tmp_mem.add("alpha"))
    id2 = _run(tmp_mem.add("beta"))
    assert id1 != id2


# ---------------------------------------------------------------------------
# size
# ---------------------------------------------------------------------------


def test_size_reflects_added_entries(tmp_mem: PersistentMemory) -> None:
    assert _run(tmp_mem.size()) == 0
    _run(tmp_mem.add("one"))
    _run(tmp_mem.add("two"))
    assert _run(tmp_mem.size()) == 2


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------


def test_search_finds_matching_content(tmp_mem: PersistentMemory) -> None:
    _run(tmp_mem.add("The quick brown fox"))
    _run(tmp_mem.add("The lazy dog"))
    results = _run(tmp_mem.search("quick"))
    assert len(results) == 1
    assert "quick" in results[0].content.lower()


def test_search_case_insensitive(tmp_mem: PersistentMemory) -> None:
    _run(tmp_mem.add("Python is great"))
    results = _run(tmp_mem.search("PYTHON"))
    assert len(results) == 1


def test_search_returns_empty_when_no_match(tmp_mem: PersistentMemory) -> None:
    _run(tmp_mem.add("unrelated content"))
    results = _run(tmp_mem.search("xyzzy_not_there"))
    assert results == []


def test_search_respects_limit(tmp_mem: PersistentMemory) -> None:
    for i in range(10):
        _run(tmp_mem.add(f"item {i}"))
    results = _run(tmp_mem.search("item", limit=3))
    assert len(results) <= 3


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_removes_entry(tmp_mem: PersistentMemory) -> None:
    entry_id = _run(tmp_mem.add("to be deleted"))
    assert _run(tmp_mem.delete(entry_id)) is True
    assert _run(tmp_mem.get(entry_id)) is None
    assert _run(tmp_mem.size()) == 0


def test_delete_unknown_returns_false(tmp_mem: PersistentMemory) -> None:
    assert _run(tmp_mem.delete("__ghost__")) is False


def test_delete_rewrite_keeps_other_entries(tmp_mem: PersistentMemory) -> None:
    id1 = _run(tmp_mem.add("keep this"))
    id2 = _run(tmp_mem.add("delete this"))
    _run(tmp_mem.delete(id2))
    assert _run(tmp_mem.get(id1)) is not None
    assert _run(tmp_mem.size()) == 1


# ---------------------------------------------------------------------------
# clear
# ---------------------------------------------------------------------------


def test_clear_empties_store(tmp_mem: PersistentMemory) -> None:
    _run(tmp_mem.add("a"))
    _run(tmp_mem.add("b"))
    _run(tmp_mem.clear())
    assert _run(tmp_mem.size()) == 0


def test_clear_removes_file(tmp_mem: PersistentMemory) -> None:
    store_path = tmp_mem._path
    _run(tmp_mem.add("x"))
    assert store_path.exists()
    _run(tmp_mem.clear())
    assert not store_path.exists()


# ---------------------------------------------------------------------------
# persistence — data survives across instances
# ---------------------------------------------------------------------------


def test_data_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "persist.jsonl"
    mem1 = PersistentMemory(path)
    entry_id = _run(mem1.add("persisted content", metadata={"v": 1}))

    mem2 = PersistentMemory(path)
    entry = _run(mem2.get(entry_id))
    assert entry is not None
    assert entry.content == "persisted content"
    assert entry.metadata == {"v": 1}


def test_size_after_reload(tmp_path: Path) -> None:
    path = tmp_path / "reload.jsonl"
    mem1 = PersistentMemory(path)
    _run(mem1.add("x"))
    _run(mem1.add("y"))
    _run(mem1.add("z"))

    mem2 = PersistentMemory(path)
    assert _run(mem2.size()) == 3


def test_search_after_reload(tmp_path: Path) -> None:
    path = tmp_path / "reload_search.jsonl"
    mem1 = PersistentMemory(path)
    _run(mem1.add("reload this content"))

    mem2 = PersistentMemory(path)
    results = _run(mem2.search("reload"))
    assert len(results) == 1


# ---------------------------------------------------------------------------
# MemoryEntry serialization
# ---------------------------------------------------------------------------


def test_memory_entry_round_trip() -> None:
    entry = MemoryEntry(
        id="abc123",
        content="hello",
        metadata={"source": "test"},
        timestamp=1000.0,
    )
    data = entry.to_dict()
    restored = MemoryEntry.from_dict(data)
    assert restored.id == entry.id
    assert restored.content == entry.content
    assert restored.metadata == entry.metadata
    assert restored.timestamp == entry.timestamp


def test_memory_entry_from_dict_defaults() -> None:
    entry = MemoryEntry.from_dict({"id": "x", "content": "y"})
    assert entry.metadata == {}
    assert entry.timestamp > 0
