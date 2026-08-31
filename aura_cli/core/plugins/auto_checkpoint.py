"""AutoCheckpoint plugin — creates a git snapshot after every file-editing tool call.

Hooks used: ``AFTER_TOOL_CALL``

Behaviour:
- Watches for tools whose names contain ``edit``, ``write``, or ``create`` (case-insensitive).
- After each such call, stages all tracked changes and creates a commit tagged
  ``[aura-auto]`` with the tool name and a short timestamp.
- Skips silently when the workspace is not a git repo or git is not on PATH.
- No checkpoint is created if there are no staged changes (nothing to commit).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import shutil
import subprocess
from typing import Callable

from aura_cli.application.extensions.plugins import (
    AuraPlugin,
    PluginContext,
    PluginHook,
    PluginMetadata,
)

_WATCHED_KEYWORDS = ("edit", "write", "create")


class AutoCheckpointPlugin(AuraPlugin):
    """Creates automatic git checkpoints after file-editing tool calls."""

    @property
    def metadata(self) -> PluginMetadata:
        return PluginMetadata(
            name="auto_checkpoint",
            version="1.0.0",
            description="Git snapshot after every file-editing tool call.",
            author="AuraCli Core Team",
        )

    def get_hooks(self) -> dict[PluginHook, Callable[[PluginContext], None]]:
        return {PluginHook.AFTER_TOOL_CALL: self._on_after_tool_call}

    def _on_after_tool_call(self, context: PluginContext) -> None:
        tool_name: str = context.get("tool_name", "")
        if not any(kw in tool_name.lower() for kw in _WATCHED_KEYWORDS):
            return

        project_root = context.get("project_root") or Path.cwd()
        self._try_checkpoint(Path(project_root), tool_name)

    def _try_checkpoint(self, root: Path, tool_name: str) -> None:
        if not shutil.which("git"):
            return
        if not (root / ".git").is_dir():
            return
        try:
            # Stage all tracked modifications
            subprocess.run(
                ["git", "add", "-u"],
                cwd=root,
                capture_output=True,
                check=False,
            )
            # Check if there is anything to commit
            result = subprocess.run(
                ["git", "diff", "--cached", "--quiet"],
                cwd=root,
                capture_output=True,
            )
            if result.returncode == 0:
                return  # Nothing staged
            timestamp = datetime.now().strftime("%H:%M:%S")
            message = f"[aura-auto] {tool_name} @ {timestamp}"
            subprocess.run(
                ["git", "commit", "-m", message, "--no-verify"],
                cwd=root,
                capture_output=True,
                check=False,
            )
        except OSError:
            pass  # git unavailable or not a repo — fail silently
