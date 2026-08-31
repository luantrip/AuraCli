"""
Tangent mode for Aura CLI.

Allows creating conversation checkpoints to explore tangential topics
without polluting the main conversation.

Inspired by Kiro CLI's tangent mode feature.
"""

from aura_cli.core.tangent.manager import TangentManager, TangentState

__all__ = ["TangentManager", "TangentState"]
