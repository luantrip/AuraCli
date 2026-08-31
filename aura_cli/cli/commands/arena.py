"""Public /arena command and deterministic bracket setup."""

from __future__ import annotations

from pathlib import Path
import shlex
from typing import Any, Optional

from aura_cli.application.artifacts import ArtifactLayout
from aura_cli.cli.workers.arena_worker import ArenaWorker


def handle_arena(args: str, app_loop: Any = None) -> Optional[str]:
    tokens = shlex.split(args)
    count, seed = 100, 0
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
        task_parts.append(token)
        index += 1
    task = " ".join(task_parts) or "Execute a robust solution for the requested task."
    root = ArtifactLayout(project_root=getattr(app_loop, "project_root", None)).project("arena")
    worker = ArenaWorker(task, project_root=Path(root).parents[1], agents=count, seed=seed)
    worker.start()
    return f"Arena iniciada: {count} competidores. Artefato: {root / 'arena.json'}"
