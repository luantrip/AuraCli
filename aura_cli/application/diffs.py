"""Surface-independent helpers for presenting file changes."""

from dataclasses import dataclass
from difflib import unified_diff
from pathlib import Path
import subprocess
from typing import Optional


@dataclass(frozen=True)
class WorkspaceDiff:
    """Bounded, serializable view of the current workspace changes."""

    project_root: str
    status: str
    changed_files: tuple[str, ...]
    patch: str
    truncated: bool = False

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_files or self.patch.strip())

    def to_dict(self) -> dict[str, object]:
        """Return the snapshot in a worker/result-friendly shape."""
        return {
            "project_root": self.project_root,
            "status": self.status,
            "changed_files": list(self.changed_files),
            "patch": self.patch,
            "truncated": self.truncated,
            "has_changes": self.has_changes,
        }

    def render(self, max_chars: int = 12_000) -> str:
        """Render a bounded context block for an agent prompt."""
        patch = self.patch[:max_chars]
        suffix = "\n[diff truncada; use git_diff_context para consultar o restante]" if self.truncated else ""
        files = ", ".join(self.changed_files) or "nenhum"
        return (
            "**WORKSPACE DIFF (estado atual, não assuma que está limpo):**\n"
            f"- raiz: {self.project_root}\n"
            f"- arquivos alterados: {files}\n"
            f"- status Git:\n{self.status or '(vazio)'}\n"
            f"- patch:\n{patch or '(sem patch rastreável)'}{suffix}"
        )


def _run_git(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    if result.returncode != 0:
        return ""
    return result.stdout


def _status_paths(status: str) -> list[str]:
    paths: list[str] = []
    for line in status.splitlines():
        if not line or line.startswith("##"):
            continue
        value = line[3:] if len(line) >= 3 else line
        if " -> " in value:
            value = value.rsplit(" -> ", 1)[-1]
        value = value.strip().strip('"')
        if value and value not in paths:
            paths.append(value)
    return paths


def capture_workspace_diff(
    project_root: Optional[Path] = None,
    *,
    max_chars: int = 12_000,
) -> WorkspaceDiff:
    """Capture tracked, staged and untracked changes for an agent.

    Untracked text files are represented as new-file patches because ordinary
    ``git diff`` does not include them. Binary and unreadable files remain in
    the changed-file list without their contents.
    """
    root = Path(project_root or Path.cwd()).resolve()
    status = _run_git(root, "status", "--short", "--branch")
    if not status:
        return WorkspaceDiff(str(root), "", (), "")

    changed_files = _status_paths(status)
    patch = _run_git(root, "diff", "--no-ext-diff", "--unified=3", "HEAD", "--")
    untracked = _run_git(root, "ls-files", "--others", "--exclude-standard")
    for relative in untracked.splitlines():
        if relative not in changed_files:
            changed_files.append(relative)
        path = root / relative
        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
        patch += "\n" + "\n".join(generate_new_file_diff(relative, content)) + "\n"

    truncated = len(patch) > max_chars
    return WorkspaceDiff(
        project_root=str(root),
        status=status.strip(),
        changed_files=tuple(changed_files),
        patch=patch[:max_chars],
        truncated=truncated,
    )


def generate_unified_diff(
    file_path: str,
    old_content: str,
    new_content: str,
) -> list[str]:
    """Return a unified diff between two versions of a file."""
    return list(
        unified_diff(
            old_content.splitlines(keepends=True),
            new_content.splitlines(keepends=True),
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )
    )


def generate_new_file_diff(file_path: str, content: str) -> list[str]:
    """Return unified-diff lines for a newly created file."""
    lines = [
        "--- /dev/null",
        f"+++ b/{file_path}",
        f"@@ -0,0 +1,{len(content.splitlines())} @@",
    ]
    lines.extend(f"+{line}" for line in content.splitlines())
    return lines
