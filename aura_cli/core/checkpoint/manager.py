"""
Checkpoint manager for Git-based state snapshots.

Enables safe experimentation with undo/redo capabilities.

Design note — two checkpoint systems exist intentionally:
  - This module (``core/checkpoint/manager.py``): Git-based snapshots of the
    *project filesystem*. Exposed via the ``/checkpoint`` CLI command. Use this
    to save/restore the state of files on disk.
  - ``core/agents/checkpointable_workflow.py``: JSON-based snapshots of
    *workflow execution state* (step results, retry counters). Used internally
    by the AGI workflow executor to resume long-running tasks after failures.

They serve different purposes and should not be merged.
"""

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class Checkpoint:
    """Checkpoint information."""

    id: str
    description: str
    timestamp: datetime
    files_changed: List[str]
    conversation_state: Optional[Dict[str, Any]] = None


class CheckpointManager:
    """
    Git-based checkpointing for safe experimentation.

    Creates shadow Git repository for tracking changes without
    affecting main repository.

    Example:
        >>> manager = CheckpointManager()
        >>> checkpoint = manager.create("basic structure")
        >>> # Make changes...
        >>> manager.restore(checkpoint.id)
    """

    def __init__(
        self,
        shadow_dir: Optional[Path] = None,
        workspace_root: Optional[Path] = None,
    ):
        """Initialize the instance with one canonical worktree root."""
        from aura_cli.core.paths import ArtifactLayout

        if workspace_root is not None:
            resolved_root = Path(workspace_root).expanduser().resolve()
        elif shadow_dir is not None:
            resolved_root = Path(shadow_dir).expanduser().resolve().parent
        else:
            configured_root = os.environ.get("AURA_PROJECT_ROOT")
            if configured_root:
                resolved_root = Path(configured_root).expanduser().resolve()
            else:
                from aura_cli.core.tools.file_system import get_allowed_base_dir

                resolved_root = Path(get_allowed_base_dir()).expanduser().resolve()
        self.workspace_root = resolved_root
        self.shadow_dir = shadow_dir or ArtifactLayout(resolved_root).project(
            ".checkpoints"
        )
        self.conversation_map: Dict[str, Dict[str, Any]] = {}
        self.initialized = False

    def init(self) -> bool:
        """
        Initialize shadow Git repository.

        Returns:
            True if successful
        """
        if self.initialized:
            return True

        try:
            self.shadow_dir.mkdir(parents=True, exist_ok=True)

            subprocess.run(
                ["git", "init", "--bare"],
                cwd=self.shadow_dir,
                check=True,
                capture_output=True,
            )

            self.initialized = True
            return True

        except Exception:
            return False

    def create(
        self, description: str, conversation_state: Optional[Dict[str, Any]] = None
    ) -> Optional[Checkpoint]:
        """
        Create checkpoint with current state.

        Args:
            description: Checkpoint description
            conversation_state: Optional conversation state to save

        Returns:
            Checkpoint object or None if failed
        """
        if not self.initialized and not self.init():
            return None

        try:
            env = {
                **os.environ,
                "GIT_DIR": str(self.shadow_dir),
                "GIT_WORK_TREE": str(self.workspace_root),
            }

            subprocess.run(
                ["git", "add", "-A"], env=env, check=True, capture_output=True
            )

            subprocess.run(
                ["git", "commit", "-m", description],
                env=env,
                capture_output=True,
                text=True,
            )

            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            commit_hash = hash_result.stdout.strip()[:8]
            files_changed = self._get_changed_files(env)
            checkpoint = Checkpoint(
                id=commit_hash,
                description=description,
                timestamp=datetime.now(),
                files_changed=files_changed,
                conversation_state=conversation_state,
            )

            if conversation_state:
                self.conversation_map[commit_hash] = deepcopy(conversation_state)

            # DEAD-NEW-07: emit CHECKPOINT_CREATED event
            try:
                import logging as _logging

                _logging.getLogger(__name__).debug(
                    f"checkpoint_created: id={commit_hash} desc={description!r} files={len(files_changed)}"
                )
            except Exception:
                # Logging failure must not abort checkpoint creation.
                pass

            return checkpoint

        except Exception:
            return None

    def list(self, limit: int = 10) -> List[Checkpoint]:
        """
        List checkpoints.

        Args:
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoints
        """
        if not self.initialized:
            return []

        try:
            env = {**os.environ, "GIT_DIR": str(self.shadow_dir)}

            result = subprocess.run(
                ["git", "log", f"--max-count={limit}", "--format=%H|%s|%at"],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            checkpoints = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue

                parts = line.split("|")
                if len(parts) < 3:
                    continue

                commit_hash = parts[0][:8]
                description = parts[1]
                timestamp = datetime.fromtimestamp(int(parts[2]))
                files_changed = self._get_files_in_commit(commit_hash, env)

                checkpoint = Checkpoint(
                    id=commit_hash,
                    description=description,
                    timestamp=timestamp,
                    files_changed=files_changed,
                    conversation_state=self.conversation_map.get(commit_hash),
                )

                checkpoints.append(checkpoint)

            return checkpoints

        except Exception:
            return []

    def restore(
        self, checkpoint_id: str, hard: bool = False
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Restore to checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to restore
            hard: If True, delete files created after checkpoint

        Returns:
            Tuple of (success, conversation_state)
        """
        if not self.initialized:
            return False, None

        try:
            env = {
                **os.environ,
                "GIT_DIR": str(self.shadow_dir),
                "GIT_WORK_TREE": str(self.workspace_root),
            }

            if hard:
                subprocess.run(
                    ["git", "checkout", "-f", checkpoint_id],
                    env=env,
                    check=True,
                    capture_output=True,
                )

                subprocess.run(
                    ["git", "clean", "-fd"], env=env, check=True, capture_output=True
                )
            else:
                subprocess.run(
                    ["git", "checkout", checkpoint_id, "--", "."],
                    env=env,
                    check=True,
                    capture_output=True,
                )

            conversation_state = self.conversation_map.get(checkpoint_id)

            return True, conversation_state

        except Exception:
            return False, None

    def diff(self, checkpoint1: str, checkpoint2: str = "HEAD") -> Optional[str]:
        """
        Show diff between checkpoints.

        Args:
            checkpoint1: First checkpoint ID
            checkpoint2: Second checkpoint ID (default: HEAD)

        Returns:
            Diff output or None if failed
        """
        if not self.initialized:
            return None

        try:
            env = {**os.environ, "GIT_DIR": str(self.shadow_dir)}

            result = subprocess.run(
                ["git", "diff", checkpoint1, checkpoint2],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )

            return result.stdout

        except Exception:
            return None

    def clean(self) -> bool:
        """
        Delete shadow repository.

        Returns:
            True if successful
        """
        try:
            import shutil

            if self.shadow_dir.exists():
                shutil.rmtree(self.shadow_dir)
            self.initialized = False
            self.conversation_map.clear()
            return True
        except Exception:
            return False

    def _get_changed_files(self, env: Dict[str, str]) -> List[str]:
        """Get list of changed files."""
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "--cached"],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            return [f for f in result.stdout.strip().split("\n") if f]
        except Exception:
            return []

    def _get_files_in_commit(self, commit_hash: str, env: Dict[str, str]) -> List[str]:
        """Get files changed in commit."""
        try:
            result = subprocess.run(
                ["git", "show", "--name-only", "--format=", commit_hash],
                env=env,
                capture_output=True,
                text=True,
                check=True,
            )
            return [f for f in result.stdout.strip().split("\n") if f]
        except Exception:
            return []
