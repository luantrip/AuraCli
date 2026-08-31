"""Dynamic context pruning for conversation history.

Replaces obsolete tool outputs with compact summary markers before context is
sent to the LLM. Pruned content is preserved in the full session log for audit;
only the LLM-visible context is trimmed.

Inspired by the ``dynamic-context-pruning`` plugin for OpenCode, adapted to
AuraCli's conversation history format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, MutableSequence


@dataclass(frozen=True)
class PruningRule:
    """A single rule describing which tool outputs are prunable."""

    tool_name: str
    reason: str
    min_age_turns: int = 0


@dataclass(frozen=True)
class PrunedEntry:
    """A compact marker replacing pruned tool content."""

    tool_name: str
    original_chars: int
    reason: str
    turn_index: int

    def render(self) -> str:
        return (
            f"[PRUNED: {self.tool_name} — {self.original_chars} chars, "
            f"{self.reason} at turn {self.turn_index}]"
        )


@dataclass
class PruningConfig:
    """Configuration for the context pruner."""

    retention_window: int = 10
    keep_last_n: int = 3
    rules: list[PruningRule] = field(default_factory=list)
    enabled: bool = True

    def __post_init__(self) -> None:
        if not self.rules:
            self.rules = _default_rules()


def _default_rules() -> list[PruningRule]:
    """Return the built-in pruning rules."""
    return [
        PruningRule(
            tool_name="read_file",
            reason="file was subsequently modified",
            min_age_turns=2,
        ),
        PruningRule(
            tool_name="list_directory",
            reason="directory listing is stale",
            min_age_turns=3,
        ),
        PruningRule(
            tool_name="tree_view",
            reason="tree structure is stale",
            min_age_turns=3,
        ),
        PruningRule(
            tool_name="run_shell_command",
            reason="command output from completed step",
            min_age_turns=4,
        ),
    ]


def _find_tool_turn_range(
    history: MutableSequence[dict[str, Any]],
) -> list[tuple[int, str, str]]:
    """Return (index, tool_name, content) for every tool message in history."""
    entries: list[tuple[int, str, str]] = []
    for idx, msg in enumerate(history):
        if msg.get("role") == "tool":
            name = msg.get("name", "")
            content = msg.get("content", "")
            entries.append((idx, name, content))
    return entries


def _was_file_modified_after(
    history: MutableSequence[dict[str, Any]],
    tool_index: int,
    file_path: str | None,
) -> bool:
    """Check whether a file path was written/edited after the given tool index."""
    if file_path is None:
        return False
    for msg in history[tool_index + 1 :]:
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for call in msg["tool_calls"]:
                fn = call.get("function", {})
                name = fn.get("name", "")
                if name in ("write_file", "edit_file"):
                    args_raw = fn.get("arguments", "{}")
                    try:
                        import json

                        args = (
                            json.loads(args_raw)
                            if isinstance(args_raw, str)
                            else args_raw
                        )
                        if args.get("path") == file_path:
                            return True
                    except (json.JSONDecodeError, TypeError):
                        continue
    return False


def _extract_path_from_args(
    history: MutableSequence[dict[str, Any]], tool_index: int
) -> str | None:
    """Extract the file path from the assistant tool_call preceding a tool result."""
    for msg in reversed(history[:tool_index]):
        if msg.get("role") == "assistant" and msg.get("tool_calls"):
            for call in msg["tool_calls"]:
                fn = call.get("function", {})
                args_raw = fn.get("arguments", "{}")
                try:
                    import json

                    args = (
                        json.loads(args_raw) if isinstance(args_raw, str) else args_raw
                    )
                    path = args.get("path")
                    if path:
                        return path
                except (json.JSONDecodeError, TypeError):
                    continue
    return None


def prune_context(
    history: MutableSequence[dict[str, Any]],
    config: PruningConfig | None = None,
) -> list[PrunedEntry]:
    """Prune obsolete tool outputs in-place, returning what was pruned.

    The history is modified in-place — pruned tool messages have their
    ``content`` replaced with a compact ``[PRUNED: ...]`` marker.  The original
    content is not preserved in the history (callers should snapshot before
    pruning if audit is needed).

    Parameters
    ----------
    history:
        The conversation history list (modified in-place).
    config:
        Pruning configuration. Defaults to :class:`PruningConfig` defaults.

    Returns
    -------
    list[PrunedEntry]
        Entries describing what was pruned, for logging or audit.
    """
    if config is None:
        config = PruningConfig()

    if not config.enabled or not history:
        return []

    tool_entries = _find_tool_turn_range(history)
    if not tool_entries:
        return []

    total_tools = len(tool_entries)
    pruned: list[PrunedEntry] = []
    rule_by_name = {rule.tool_name: rule for rule in config.rules}

    for turn_num, (idx, tool_name, content) in enumerate(tool_entries):
        # Never prune the last N tool outputs
        if turn_num >= total_tools - config.keep_last_n:
            break

        rule = rule_by_name.get(tool_name)
        if rule is None:
            continue

        age = total_tools - turn_num - 1
        if age < rule.min_age_turns:
            continue

        if tool_name == "read_file":
            file_path = _extract_path_from_args(history, idx)
            if not _was_file_modified_after(history, idx, file_path):
                continue

        # Prune
        entry = PrunedEntry(
            tool_name=tool_name,
            original_chars=len(content),
            reason=rule.reason,
            turn_index=turn_num,
        )
        history[idx]["content"] = entry.render()
        pruned.append(entry)

    return pruned


def estimate_pruning_savings(
    history: MutableSequence[dict[str, Any]],
    config: PruningConfig | None = None,
) -> dict[str, int]:
    """Estimate how many characters would be pruned without modifying history.

    Returns a dict with ``prunable_count``, ``prunable_chars``, and
    ``total_tool_chars`` for observability.
    """
    if config is None:
        config = PruningConfig()

    if not config.enabled or not history:
        return {"prunable_count": 0, "prunable_chars": 0, "total_tool_chars": 0}

    tool_entries = _find_tool_turn_range(history)
    total_tools = len(tool_entries)
    rule_by_name = {rule.tool_name: rule for rule in config.rules}

    prunable_count = 0
    prunable_chars = 0
    total_tool_chars = 0

    for turn_num, (idx, tool_name, content) in enumerate(tool_entries):
        total_tool_chars += len(content)
        if turn_num >= total_tools - config.keep_last_n:
            break
        rule = rule_by_name.get(tool_name)
        if rule is None:
            continue
        age = total_tools - turn_num - 1
        if age < rule.min_age_turns:
            continue
        if tool_name == "read_file":
            file_path = _extract_path_from_args(history, idx)
            if not _was_file_modified_after(history, idx, file_path):
                continue
        prunable_count += 1
        prunable_chars += len(content)

    return {
        "prunable_count": prunable_count,
        "prunable_chars": prunable_chars,
        "total_tool_chars": total_tool_chars,
    }


__all__ = [
    "PrunedEntry",
    "PruningConfig",
    "PruningRule",
    "estimate_pruning_savings",
    "prune_context",
]
