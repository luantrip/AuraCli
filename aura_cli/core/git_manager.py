"""Git Manager — Version Control and Safety.

Manages Git integration for dirty-state checks, checkpoints and safe writes.
"""

from datetime import datetime
from pathlib import Path
import subprocess
from typing import Dict, List, Optional, Tuple


class GitManager:
    """Manages Git operations for the workspace."""

    def __init__(self, project_root: Path):
        """Initialise the GitManager."""
        self.project_root = project_root
        self.git_dir = project_root / ".git"
        self._is_git_repo = self.git_dir.exists()

    def is_git_repository(self) -> bool:
        """Return True if the directory is a Git repository."""
        return self._is_git_repo

    def check_dirty_state(self) -> Tuple[bool, List[str]]:
        """Return True if the working tree has uncommitted changes."""
        if not self._is_git_repo:
            return False, []

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            modified_files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    # git status --porcelain format: XY filename
                    status = line[:2]
                    filename = line[3:].strip()
                    if status != "??":  # Ignore untracked files
                        modified_files.append(filename)

            return len(modified_files) > 0, modified_files

        except subprocess.CalledProcessError:
            return False, []
        except FileNotFoundError:
            return False, []

    def create_checkpoint(self, message: Optional[str] = None) -> Optional[str]:
        """Create a checkpoint commit before large changes."""
        if not self._is_git_repo:
            return None

        is_dirty, modified_files = self.check_dirty_state()
        if not is_dirty or not modified_files:
            return None

        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.project_root,
                capture_output=True,
                check=True,
            )

            if not message:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"aura-wip: Auto-checkpoint at {timestamp}"

            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            return hash_result.stdout.strip()

        except subprocess.CalledProcessError:
            return None

    def get_last_checkpoint(self) -> Optional[Dict[str, str]]:
        """Return the most recent checkpoint commit hash."""
        if not self._is_git_repo:
            return None

        try:
            result = subprocess.run(
                ["git", "log", "--grep=aura-wip", "--format=%H|%s|%ai", "-n", "1"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )

            if not result.stdout.strip():
                return None

            parts = result.stdout.strip().split("|")
            if len(parts) == 3:
                return {
                    "hash": parts[0],
                    "message": parts[1],
                    "date": parts[2],
                }

        except subprocess.CalledProcessError:
            pass

        return None

    def validate_before_write(self) -> Tuple[bool, Optional[str]]:
        """Return (is_safe, warning_message) before a write."""
        if not self._is_git_repo:
            return True, None

        is_dirty, modified_files = self.check_dirty_state()

        if is_dirty:
            files_list = "\n  - ".join(modified_files[:10])
            if len(modified_files) > 10:
                files_list += f"\n  ... e mais {len(modified_files) - 10} arquivo(s)"

            warning = (
                f"⚠️  Você tem {len(modified_files)} arquivo(s) "
                f"com mudanças não commitadas:\n"
                f"  - {files_list}\n\n"
                f"Recomendação: Faça commit ou stash antes de continuar.\n"
                f"Posso criar um checkpoint automático? (aura-wip commit)"
            )
            return False, warning

        return True, None

    def get_current_branch(self) -> Optional[str]:
        """Return the current branch name, or None."""
        if not self._is_git_repo:
            return None

        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout.strip() or None
        except subprocess.CalledProcessError:
            return None
