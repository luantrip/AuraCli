"""/skill usage string advertises every implemented subcommand.

`search` was implemented but missing from the usage line, so users could not
discover it. Also pins the user-facing strings to English.
"""

from __future__ import annotations

from aura_cli.cli.commands.skill import handle_skill


def test_usage_lists_every_implemented_subcommand() -> None:
    usage = handle_skill("unknown-command")  # unrecognized -> usage fallback
    assert usage is not None
    for subcommand in ("list", "install", "remove", "status", "pack", "search"):
        assert subcommand in usage, subcommand


def test_usage_is_english() -> None:
    usage = handle_skill("unknown-command")
    assert usage is not None
    assert usage.startswith("Usage:")
    # No leftover Portuguese from the previous version.
    assert "Uso:" not in usage


def test_empty_list_message_is_english(tmp_path, monkeypatch) -> None:
    # Point the skills root at an empty temp dir via ArtifactLayout project root.
    class _Loop:
        project_root = tmp_path

    result = handle_skill("list", app_loop=_Loop())
    assert result == "No skills installed."
