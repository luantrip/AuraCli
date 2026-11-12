"""Natural language Git command parser (Portuguese) for Aura CLI.

Parses natural-language descriptions like "far commit das changes" into
Git action dicts, extracts commit messages from free text, and generates
commit message suggestions. Supports: commit, status, log, diff, branch.
"""

import re
from typing import Dict, List, Optional


def parse_natural_git_command(command: str) -> Dict:
    """Parse a natural-language Git command into a Git action dict.

    Args:
        command: Natural-language description (e.g. "far commit changes").

    Returns:
        Dict with 'action' (commit, status, log, diff, branch, unknown)
        and relevant metadata keys.
    """
    command_lower = command.lower().strip()

    commit_patterns = [
        r"(fazer|fazer um|criar|fazer o|fazer o commit|commitar|salvar)\s+(?:um\s+)?commit",
        r"commitar\s+(?:as\s+)?(?:mudanças|alterações|código|tudo)",
        r"salvar\s+(?:as\s+)?(?:mudanças|alterações)",

        r"commit\s+(?:the\s+)?(?:changes|code)",
        r"save\s+(?:the\s+)?(?:changes)",
        r"make\s+(?:a\s+)?commit\s+(?:of\s+)?(?:the\s+)?(?:changes)",
    ]

    for pattern in commit_patterns:
        if re.search(pattern, command_lower):
            return {
                "action": "commit",
                "auto_stage": True,
                "extract_message": True,
                "original": command,
            }

    status_patterns = [
        r"status\s+(?:of\s+)?(?:the\s+)?(?:repository|git|project)",
        r"(view|show|list|display)\s+(?:the\s+)?(?:changes|status|pending)?",
        r"pending\s+changes?",
        r"o\s+que\s+mudou\b",
        r"(ver|mostrar|listar)\s+(?:as\s+)?(?:mudanças|status|alterações)",
        r"mudanças?\s+pendentes",
        r"status\s+(?:do\s+)?(?:repositório|git|projeto)",

        r"what\s+changed\s+(?:in\s+the\s+)?(?:repository|project)",
    ]

    for pattern in status_patterns:
        if re.search(pattern, command_lower):
            return {"action": "status", "original": command}

    log_patterns = [
        r"(history|commits?|log)\s+(?:of\s+)?(?:commits?|changes|project)",
        r"(últimos|recentes)\s+commits?",
        r"histórico\s+(?:de\s+)?commits?",
        r"log\s+(?:de\s+)?commits?",

        r"ver\s+(?:o\s+)?(?:histórico|log|commits)",
        r"commits?\s+(?:anteriores|passados)",
    ]

    for pattern in log_patterns:
        if re.search(pattern, command_lower):
            return {"action": "log", "original": command}

    diff_patterns = [
        r"diff\s+(?:do\s+)?(?:código|arquivo)",
        r"(?:ver|mostrar)\s+(?:as\s+)?diferenças",
        r"(diferença|diferenças)\s+(?:no\s+)?(?:código|arquivo)",
        r"ver\s+(?:as\s+)?diff\s+(?:no\s+)?(?:código|arquivo)",
        r"comparar\s+(?:mudanças|versões)",
        r"o\s+que\s+foi\s+alterado",
        r"o\s+que\s+foi\s+alterado\s+(?:no\s+)?(?:código|arquivo)",
        r"mudanças\s+no\s+código",
    ]

    for pattern in diff_patterns:
        if re.search(pattern, command_lower):
            return {"action": "diff", "original": command}

    branch_patterns = [
        r"(branches?|ramos?|branch)",
        r"ver\s+(?:as\s+)?(?:branches?|ramos?)",
        r"listar\s+(?:as\s+)?(?:branches?|ramos?)",
    ]

    for pattern in branch_patterns:
        if re.search(pattern, command_lower):
            return {"action": "branch", "original": command}

    return {"action": "unknown", "original": command}


def extract_commit_message(command: str) -> Optional[str]:
    """Extract a commit message from a natural-language command."""
    patterns = [
        r"com\s+mensagem\s+['\"](.+?)['\"]",
        r"mensagem\s*:\s*['\"]?(.+?)['\"]?(?:\s|$)",
        r"dizendo\s+['\"](.+?)['\"]",
        r"dizendo\s+([^\"']+?)(?:\s|\.|$)",
        r"como\s+['\"](.+?)['\"]",
        r"['\"]([^'\"]+?)['\"]",
    ]

    for pattern in patterns:
        match = re.search(pattern, command, re.IGNORECASE)
        if match:
            message = match.group(1).strip()
            if message and len(message) > 2:
                return message

    return None


def suggest_commit_message(changes: List[str] | None = None) -> str:
    """Suggest a conventional-commits message based on changed files.

    Args:
        changes: List of git-status --short lines
            (e.g. ["A  new_file.py", "M  existing.py"]).

    Returns:
        Suggested commit message string (e.g. "feat: atualizar 3 arquivos").
    """
    if not changes:
        return "feat: automatic changes"

    has_new_files = any(
        c.strip().startswith("A")
        or c.strip().startswith("??")
        or "new file" in c.lower()
        or c.strip().startswith("A ")
        for c in changes
    )
    has_deleted = any(
        c.strip().startswith("D")
        or "deleted" in c.lower()
        or c.strip().startswith("D ")
        for c in changes
    )
    has_modified = any(
        c.strip().startswith("M")
        or "modified" in c.lower()
        or (c.strip().startswith("M ") and not has_new_files and not has_deleted)
        for c in changes
    )

    if has_new_files:
        prefix = "feat"
    elif has_deleted:
        prefix = "refactor"
    elif has_modified:
        prefix = "fix"
    else:
        prefix = "feat"

    file_count = len(changes)
    file_desc = "arquivo" if file_count == 1 else "arquivos"

    return f"{prefix}: atualizar {file_count} {file_desc}"


def format_git_action_description(action: str, parsed: Dict) -> str:
    """Return a user-friendly description of a parsed Git action.

    Args:
        action: Git action string (commit, status, log, diff, branch, unknown).
        parsed: Result dict from parse_natural_git_command.

    Returns:
        Human-readable description string.
    """
    descriptions = {
        "commit": "Create commit",
        "status": "Show repository status",
        "log": "Show commit history",
        "diff": "Show differences",
        "branch": "List branches",
        "unknown": "Unknown command",
    }

    desc = descriptions.get(action, "Unknown action")

    if action == "commit" and parsed.get("auto_stage"):
        desc += " (with auto-stage)"

    return desc
