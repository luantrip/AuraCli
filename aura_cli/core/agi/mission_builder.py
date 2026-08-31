"""Small adapter for constructing the AGI mission pointer."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .evidence_tree import EvidenceTree


def build_mission(root: Path, task_id: str, task: str, *,
                  conversation_history: Optional[list[dict]] = None,
                  relevant_files: Optional[list[Path]] = None) -> str:
    """Build an evidence tree and return the short pointer injected into prompts."""
    tree = EvidenceTree(root, task_id)
    tree.build(task, conversation_history=conversation_history, relevant_files=relevant_files)
    return tree.mission_pointer()
