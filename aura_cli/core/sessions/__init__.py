"""
Session System for Aura CLI.

This package provides:
- SessionManager: Persistent session storage between executions
- SessionStateManager: In-memory runtime session state
- Session: Session data model

Usage:
    # For persistent sessions:
    >>> from aura_cli.core.sessions import get_session_manager
    >>> manager = get_session_manager()

    # For runtime state:
    >>> from aura_cli.core.sessions import get_session_state
    >>> state = get_session_state()
    >>> state.initialize(project_root)
"""

from aura_cli.core.sessions.session_manager import (
    Session,
    SessionManager,
    get_session_manager,
)
from aura_cli.core.sessions.session_state import (
    SessionState,
    SessionStateManager,
    get_session_state,
    reset_session_state,
)

__all__ = [
    # Persistent Sessions
    "Session",
    "SessionManager",
    # Runtime State
    "SessionState",
    "SessionStateManager",
    "get_session_manager",
    "get_session_state",
    "reset_session_state",
]
