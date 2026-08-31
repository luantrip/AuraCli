"""File-browser presentation decisions."""

from pathlib import Path
import stat

import pytest

from aura_cli.application.presentation.file_browser import (
    append_navigation_path,
    format_file_permissions,
    format_file_size,
    plan_duplicate_destination,
    plan_transfer_destination,
    resolve_child_path,
)


def test_file_size_boundaries_and_negative_input() -> None:
    assert format_file_size(-1) == "0 B"
    assert format_file_size(1023) == "1023 B"
    assert format_file_size(1024) == "1.0 KB"
    assert format_file_size(2 * 1024**2) == "2.0 MB"


def test_permissions_use_unix_owner_group_other_order() -> None:
    mode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP
    assert format_file_permissions(mode) == "rw-r-----"


def test_navigation_discards_forward_paths_and_avoids_duplicates() -> None:
    history = [Path("/one"), Path("/two"), Path("/three")]
    updated, index = append_navigation_path(history, 1, Path("/four"))
    duplicate, duplicate_index = append_navigation_path(updated, index, Path("/four"))

    assert updated == [Path("/one"), Path("/two"), Path("/four")]
    assert index == 2
    assert duplicate == updated
    assert duplicate_index == index


def test_child_path_rejects_absolute_and_traversal_names() -> None:
    assert resolve_child_path(Path("/safe"), "file.txt") == Path("/safe/file.txt")
    for invalid in ("../escape", "/tmp/escape", ".", ""):
        with pytest.raises(ValueError):
            resolve_child_path(Path("/safe"), invalid)


def test_transfer_and_duplicate_plans_resolve_collisions() -> None:
    occupied = {
        Path("/dest/file.txt"),
        Path("/dest/file_copy1.txt"),
        Path("/src/file_copy.txt"),
    }
    exists = occupied.__contains__

    assert plan_transfer_destination(
        Path("/src/file.txt"), Path("/dest"), exists=exists
    ) == Path("/dest/file_copy2.txt")
    assert plan_duplicate_destination(Path("/src/file.txt"), exists=exists) == Path(
        "/src/file_copy2.txt"
    )
