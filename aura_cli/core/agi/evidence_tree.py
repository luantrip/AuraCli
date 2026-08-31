"""Evidence tree builder for AGI task execution.

The evidence tree pattern (adapted from harness2/context.py) serves context to
an AGI agent as files in a structured directory rather than injecting everything
into the prompt.  The agent receives a short ``MISSION.md`` pointer instead of a
long preamble, so large context does not degrade quality.

Layout under ``<agi_artifacts_root>/<task_id>/context/``:
    task.md              — the task in natural language
    conversation/        — relevant conversation history chunks (paginated)
    codebase/            — project files identified as relevant
    rollouts/            — full transcripts of previous runs on this task
    MISSION.md           — short pointer for the agent (injected into prompt)

Usage::

    tree = EvidenceTree(root=Path("/tmp/.aura/agi/task-abc"), task_id="task-abc")
    tree.build(task="...", conversation_history=[...], relevant_files=[...])
    pointer = tree.mission_pointer()  # inject into system prompt
    # ... run agent ...
    tree.cleanup()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

# Maximum characters per conversation chunk written to disk.
_CONV_CHUNK_CHARS = 8_000
# Maximum number of codebase files copied into the evidence tree.
_MAX_CODEBASE_FILES = 30
# Maximum bytes per codebase file copied.
_MAX_FILE_BYTES = 64_000


@dataclass
class EvidenceTreeLayout:
    """Describes what actually landed in the tree (for MISSION.md generation)."""

    task_id: str
    root: Path
    has_task: bool = False
    conversation_chunks: int = 0
    codebase_files: int = 0
    rollout_ids: list[str] = field(default_factory=list)
    failed_files: list[str] = field(default_factory=list)


class EvidenceTree:
    """Builds and manages a per-task evidence directory for AGI agents.

    Args:
        root: The directory root for this task's evidence (created if absent).
        task_id: Unique identifier for the task (used in MISSION.md).
    """

    def __init__(self, root: Path, task_id: str) -> None:
        self.root = Path(root)
        self.task_id = task_id
        self._context_dir = self.root / "context"
        self._layout: Optional[EvidenceTreeLayout] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def build(
        self,
        task: str,
        *,
        conversation_history: Optional[list[dict]] = None,
        relevant_files: Optional[list[Path]] = None,
        previous_rollouts: Optional[list[tuple[str, str]]] = None,
    ) -> EvidenceTreeLayout:
        """Materialise the evidence tree on disk.

        Args:
            task: Natural-language task description.
            conversation_history: List of ``{"role": ..., "content": ...}`` dicts.
            relevant_files: Absolute paths to project files to include.
            previous_rollouts: List of ``(rollout_id, transcript_text)`` tuples.

        Returns:
            An ``EvidenceTreeLayout`` describing what was written.
        """
        self._context_dir.mkdir(parents=True, exist_ok=True)
        layout = EvidenceTreeLayout(task_id=self.task_id, root=self.root)

        # 1. task.md
        self._write_task(task, layout)

        # 2. conversation/
        if conversation_history:
            self._write_conversation(conversation_history, layout)

        # 3. codebase/
        if relevant_files:
            self._write_codebase(relevant_files, layout)

        # 4. rollouts/
        if previous_rollouts:
            self._write_rollouts(previous_rollouts, layout)

        # 5. MISSION.md
        self._write_mission(layout)

        self._layout = layout
        logger.debug(
            "EvidenceTree built for task %s: task=%s conv_chunks=%d codebase=%d rollouts=%d",
            self.task_id,
            layout.has_task,
            layout.conversation_chunks,
            layout.codebase_files,
            len(layout.rollout_ids),
        )
        return layout

    def mission_pointer(self) -> str:
        """Return the short MISSION.md content to inject into the agent prompt.

        If the tree has not been built yet, returns a minimal pointer.
        """
        mission_path = self._context_dir / "MISSION.md"
        if mission_path.exists():
            return mission_path.read_text(encoding="utf-8")
        return (
            f"Task ID: {self.task_id}\n"
            "Evidence directory not available — work from the task as stated."
        )

    def cleanup(self) -> None:
        """Remove the entire evidence tree from disk."""
        import shutil

        if self.root.exists():
            try:
                shutil.rmtree(self.root)
                logger.debug("EvidenceTree cleaned up: %s", self.root)
            except Exception as exc:
                logger.warning("Failed to clean up evidence tree %s: %s", self.root, exc)

    # ── Private helpers ───────────────────────────────────────────────────────

    def _write_task(self, task: str, layout: EvidenceTreeLayout) -> None:
        path = self._context_dir / "task.md"
        try:
            path.write_text(f"# Task\n\n{task}\n", encoding="utf-8")
            layout.has_task = True
        except Exception as exc:
            logger.warning("EvidenceTree: failed to write task.md: %s", exc)

    def _write_conversation(
        self, history: list[dict], layout: EvidenceTreeLayout
    ) -> None:
        conv_dir = self._context_dir / "conversation"
        conv_dir.mkdir(exist_ok=True)
        # Filter to meaningful messages (skip empty, skip system noise).
        messages = [
            m for m in history
            if m.get("content") and m.get("role") in ("user", "assistant")
        ]
        if not messages:
            return
        # Paginate into chunks.
        chunk: list[str] = []
        chunk_size = 0
        chunk_idx = 0

        def _flush(idx: int) -> None:
            if not chunk:
                return
            text = "\n\n---\n\n".join(chunk)
            path = conv_dir / f"chunk_{idx:03d}.md"
            try:
                path.write_text(text, encoding="utf-8")
                layout.conversation_chunks += 1
            except Exception as exc:
                logger.debug("EvidenceTree: failed to write conv chunk %d: %s", idx, exc)

        for msg in messages:
            content = str(msg.get("content", ""))
            role = msg.get("role", "unknown")
            entry = f"**{role}**: {content}"
            if chunk_size + len(entry) > _CONV_CHUNK_CHARS and chunk:
                _flush(chunk_idx)
                chunk_idx += 1
                chunk = []
                chunk_size = 0
            chunk.append(entry)
            chunk_size += len(entry)
        _flush(chunk_idx)

    def _write_codebase(
        self, files: list[Path], layout: EvidenceTreeLayout
    ) -> None:
        codebase_dir = self._context_dir / "codebase"
        codebase_dir.mkdir(exist_ok=True)
        written = 0
        for file_path in files[:_MAX_CODEBASE_FILES]:
            src = Path(file_path)
            if not src.is_file():
                layout.failed_files.append(str(src))
                continue
            try:
                content = src.read_bytes()[:_MAX_FILE_BYTES]
                dest = codebase_dir / src.name
                # Avoid collisions for same-named files from different dirs.
                if dest.exists():
                    dest = codebase_dir / f"{src.parent.name}__{src.name}"
                dest.write_bytes(content)
                written += 1
            except Exception as exc:
                layout.failed_files.append(str(src))
                logger.debug("EvidenceTree: failed to copy %s: %s", src, exc)
        layout.codebase_files = written

    def _write_rollouts(
        self, rollouts: list[tuple[str, str]], layout: EvidenceTreeLayout
    ) -> None:
        rollouts_dir = self._context_dir / "rollouts"
        rollouts_dir.mkdir(exist_ok=True)
        for rollout_id, transcript in rollouts:
            path = rollouts_dir / f"{rollout_id}.md"
            try:
                path.write_text(transcript, encoding="utf-8")
                layout.rollout_ids.append(rollout_id)
            except Exception as exc:
                logger.debug(
                    "EvidenceTree: failed to write rollout %s: %s", rollout_id, exc
                )

    def _write_mission(self, layout: EvidenceTreeLayout) -> None:
        lines: list[str] = [
            f"# Mission — Task `{self.task_id}`\n",
            "Read the files below in order and execute the task.\n",
        ]
        if layout.has_task:
            lines.append("- `context/task.md` — the task as stated\n")
        if layout.conversation_chunks > 0:
            lines.append(
                f"- `context/conversation/` — {layout.conversation_chunks} "
                f"conversation chunk(s) with relevant history\n"
            )
        if layout.codebase_files > 0:
            lines.append(
                f"- `context/codebase/` — {layout.codebase_files} relevant project file(s)\n"
            )
        if layout.rollout_ids:
            names = ", ".join(f"`{r}.md`" for r in layout.rollout_ids[:4])
            more = f" (+{len(layout.rollout_ids) - 4} more)" if len(layout.rollout_ids) > 4 else ""
            lines.append(f"- `context/rollouts/` — previous runs: {names}{more}\n")
        lines.append(
            "\nWhen you are done, write your output to the session and say TERMINATE.\n"
        )
        path = self._context_dir / "MISSION.md"
        try:
            path.write_text("".join(lines), encoding="utf-8")
        except Exception as exc:
            logger.warning("EvidenceTree: failed to write MISSION.md: %s", exc)
