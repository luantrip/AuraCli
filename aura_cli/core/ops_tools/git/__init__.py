"""Git tools for Aura Ops.

Git executor functions (git_status, git_diff, etc.) live here.
Natural-language parsers are imported from core.tools.natural_git.
"""

from pathlib import Path
import subprocess
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from aura_cli.application.diffs import capture_workspace_diff
from aura_cli.core.logger import get_logger
from aura_cli.core.tools.natural_git import (
    extract_commit_message,
    format_git_action_description,
    parse_natural_git_command,
    suggest_commit_message,
)
from aura_cli.core.ui import display_tool_call

logger = get_logger(__name__)
console = Console()


def git_status() -> str:
    """Show git working tree status."""
    display_tool_call("git_status", {})
    try:
        result = subprocess.run(
            ["git", "status", "--short", "--branch"],
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout.strip()
        console.print(output or "[green]Working tree clean[/green]")
        return output
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Unexpected error: {e}"


def git_diff(file: Optional[str] = None, staged: bool = False) -> str:
    """Show git diff."""
    display_tool_call("git_diff", {"file": file, "staged": staged})
    try:
        cmd = ["git", "diff"]
        if staged:
            cmd.append("--staged")
        if file:
            cmd.append(file)
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        output = result.stdout.strip()
        console.print(output or "[green]No differences[/green]")
        return output
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Unexpected error: {e}"


def git_diff_context(path: Optional[str] = None, max_chars: int = 12_000) -> str:
    """Return Git status plus tracked and untracked workspace changes."""
    display_tool_call("git_diff_context", {"path": path, "max_chars": max_chars})
    snapshot = capture_workspace_diff(Path(path) if path else None, max_chars=max_chars)
    rendered = snapshot.render(max_chars=max_chars)
    console.print(rendered)
    return rendered


def git_log(limit: int = 10) -> str:
    """Show recent git commits."""
    display_tool_call("git_log", {"limit": limit})
    try:
        result = subprocess.run(
            ["git", "log", f"--max-count={limit}", "--oneline"],
            capture_output=True,
            text=True,
            check=True,
        )
        output = result.stdout.strip()
        if not output:
            return "No commits found."
        console.print(output)
        return f"Displayed {limit} commits"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Unexpected error: {e}"


def git_branch() -> str:
    """List all local and remote branches."""
    display_tool_call("git_branch", {})
    try:
        result = subprocess.run(
            ["git", "branch", "-a"], capture_output=True, text=True, check=True
        )
        branches = [b for b in result.stdout.strip().split("\n") if b]
        table = Table(title="Git Branches")
        table.add_column("Branch", style="cyan")
        table.add_column("Type", style="green")
        for branch in branches:
            name = branch.strip().lstrip("*").strip()
            btype = "Remote" if name.startswith("remotes/") else "Local"
            table.add_row(name, btype)
        console.print(table)
        return f"Listed {len(branches)} branches"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Unexpected error: {e}"


def git_commit(message: str, files: Optional[List[str]] = None) -> str:
    """Create a git commit."""
    display_tool_call("git_commit", {"message": message, "files": files})
    try:
        if files:
            subprocess.run(["git", "add", *files], check=True)
        else:
            subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", message], check=True)
        msg = f"Committed: {message}"
        console.print(f"[green]{msg}[/green]")
        return msg
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    except Exception as e:
        return f"Unexpected error: {e}"


def git_commit_smart(command: str) -> str:
    """Smart commit using natural language parser."""
    display_tool_call("git_commit_smart", {"command": command})
    message = extract_commit_message(command) or suggest_commit_message()
    return git_commit(message)


def git_smart(command: str) -> str:
    """Execute git operation from natural language command."""
    display_tool_call("git_smart", {"command": command})
    parsed = parse_natural_git_command(command)
    action = parsed.get("action", "")
    dispatch = {
        "commit": lambda: git_commit_smart(command),
        "status": git_status,
        "diff": git_diff,
        "log": git_log,
        "branch": git_branch,
    }
    fn = dispatch.get(action)
    if fn:
        return fn()
    return f"Action '{action}' not recognised."


__all__ = [
    "extract_commit_message",
    "format_git_action_description",
    "git_branch",
    "git_commit",
    "git_commit_smart",
    "git_diff",
    "git_diff_context",
    "git_log",
    "git_smart",
    "git_status",
    "parse_natural_git_command",
    "suggest_commit_message",
]
