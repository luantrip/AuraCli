"""
Optional automation for user-defined workflows.

Provides a simple layer for creating and executing workflows
persisted by the user. Remains useful as lateral automation
and local customisation, but does not correspond to the canonical agent workflow of
the main runtime.al.
"""

from aura_cli.core.workflows.user_workflow import (
    UserWorkflow,
    UserWorkflowManager,
    UserWorkflowStep,
    get_workflow_manager,
)

__all__ = [
    "UserWorkflow",
    "UserWorkflowManager",
    "UserWorkflowStep",
    "get_workflow_manager",
]
