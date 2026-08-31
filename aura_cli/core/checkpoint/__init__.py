"""
Checkpointing system for Aura CLI.

Git-based checkpointing for safe experimentation and undo/redo.
Inspired by Kiro CLI's checkpoint feature.
"""

from aura_cli.core.checkpoint.manager import Checkpoint, CheckpointManager

__all__ = ["Checkpoint", "CheckpointManager"]
