"""Public /arena command and deterministic bracket setup."""

from __future__ import annotations

from pathlib import Path
import shlex
import threading
from typing import Any, Optional

from aura_cli.cli.ui.constants import UIIcons, UIStyles
from aura_cli.cli.utils.worker_factory import create_arena_worker_thread

# Module-level handle so repeated /arena calls can detect an in-flight run.
_arena_thread: Optional[threading.Thread] = None


def handle_arena(args: str, app_loop: Any = None) -> Optional[str]:
    global _arena_thread

    if _arena_thread is not None and _arena_thread.is_alive():
        return (
            f"[{UIStyles.WARNING}]{UIIcons.WARNING} "
            f"An Arena is already in progress. Wait for it to complete.[/{UIStyles.WARNING}]"
        )

    tokens = shlex.split(args)
    count, seed = 100, 0
    use_llm_judge = False
    task_parts = []
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in ("--agents", "-n") and index + 1 < len(tokens):
            count = int(tokens[index + 1])
            index += 2
            continue
        if token == "--seed" and index + 1 < len(tokens):
            seed = int(tokens[index + 1])
            index += 2
            continue
        if token == "--quick":
            count = 16
            index += 1
            continue
        if token == "--judge-llm":
            use_llm_judge = True
            index += 1
            continue
        task_parts.append(token)
        index += 1
    task = " ".join(task_parts) or "Execute a robust solution for the requested task."
    project_root = Path(getattr(app_loop, "project_root", None) or Path.cwd())
    model = getattr(app_loop, "final_model", "") or ""

    _, _arena_thread = create_arena_worker_thread(
        task=task,
        project_root=project_root,
        agents=count,
        seed=seed,
        use_llm_judge=use_llm_judge,
        model=model,
    )

    judge_label = "LLM judge" if use_llm_judge else "heuristic judge (rubric)"
    return (
        f"[{UIStyles.INFO}]{UIIcons.AURA} "
        f"Arena started in background: {count} candidates, {judge_label}. "
        f"Progress and the winner will appear in the chat.[/{UIStyles.INFO}]"
    )
