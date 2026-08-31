"""
Checkpoint and Tangent tools for AGI agents.

These tools allow agents to manage project checkpoints and conversation tangents,
enabling automatic context management during complex operations.

Features:
    - Auto-checkpoint before risky operations
    - Restore to previous states on failure
    - Tangent mode for exploratory analysis
    - Conversation history management
"""

from typing import Any, Dict, List

from aura_cli.application.workspace.context_usage import (
    get_context_percentage,
    should_compact_context,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

_checkpoint_manager = None
_tangent_manager = None


def set_checkpoint_manager(manager) -> None:
    """Set the global checkpoint manager instance."""
    global _checkpoint_manager
    _checkpoint_manager = manager


def set_tangent_manager(manager) -> None:
    """Set the global tangent manager instance."""
    global _tangent_manager
    _tangent_manager = manager


def create_checkpoint(description: str = "") -> Dict[str, Any]:
    """
    Create a checkpoint of the current project state.

    Use this tool BEFORE making significant changes to the codebase.
    This creates a Git-based snapshot that can be restored if needed.

    Args:
        description: A brief description of what the checkpoint captures
                    (e.g., "Before refactoring auth module", "Pre-deployment state")

    Returns:
        dict: Result with checkpoint_id and status

    Example:
        >>> result = create_checkpoint("Before implementing new feature")
        >>> print(result)
        {'success': True, 'checkpoint_id': 'abc123', 'message': 'Checkpoint created'}
    """
    if not _checkpoint_manager:
        return {
            "success": False,
            "error": "Checkpoint system not initialized. Run /checkpoint init first.",
        }

    try:
        if not _checkpoint_manager._initialized:
            init_result = _checkpoint_manager.init()
            if not init_result:
                return {
                    "success": False,
                    "error": "Failed to initialize checkpoint system",
                }

        checkpoint = _checkpoint_manager.create(description)

        if checkpoint:
            return {
                "success": True,
                "checkpoint_id": checkpoint.commit_hash[:8],
                "description": checkpoint.description,
                "files_changed": checkpoint.files_changed,
                "message": f"✅ Checkpoint created: {checkpoint.commit_hash[:8]}",
            }
        else:
            return {
                "success": False,
                "error": "No changes to checkpoint",
            }

    except Exception as e:
        logger.error(f"Error creating checkpoint: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def list_checkpoints() -> Dict[str, Any]:
    """
    List all available checkpoints.

    Use this to see all saved states that can be restored.

    Returns:
        dict: List of checkpoints with their IDs, descriptions, and timestamps

    Example:
        >>> result = list_checkpoints()
        >>> for cp in result['checkpoints']:
        ...     print(f"{cp['id']}: {cp['description']}")
    """
    if not _checkpoint_manager:
        return {
            "success": False,
            "error": "Checkpoint system not initialized",
            "checkpoints": [],
        }

    try:
        checkpoints = _checkpoint_manager.list()

        return {
            "success": True,
            "checkpoints": [
                {
                    "id": cp.commit_hash[:8],
                    "description": cp.description,
                    "timestamp": cp.timestamp.isoformat() if cp.timestamp else None,
                    "files_changed": cp.files_changed,
                }
                for cp in checkpoints
            ],
            "total": len(checkpoints),
        }

    except Exception as e:
        logger.error(f"Error listing checkpoints: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "checkpoints": [],
        }


def restore_checkpoint(checkpoint_id: str, hard: bool = False) -> Dict[str, Any]:
    """Restore the workspace to a checkpoint."""
    if not _checkpoint_manager:
        return {
            "success": False,
            "error": "Checkpoint system not initialized",
        }

    try:
        files_restored, _conversation = _checkpoint_manager.restore(
            checkpoint_id, hard=hard
        )

        return {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "files_restored": files_restored,
            "hard_restore": hard,
            "message": f"✅ Restored to checkpoint {checkpoint_id} ({len(files_restored)} files)",
        }

    except Exception as e:
        logger.error(f"Error restoring checkpoint: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def diff_checkpoint(checkpoint_id: str) -> Dict[str, Any]:
    """
    Show differences between current state and a checkpoint.

    Use this to see what has changed since a checkpoint was created.

    Args:
        checkpoint_id: The ID of the checkpoint to compare against

    Returns:
        dict: Diff information with changed files

    Example:
        >>> result = diff_checkpoint("abc123")
        >>> for file in result['files_changed']:
        ...     print(f"Modified: {file}")
    """
    if not _checkpoint_manager:
        return {
            "success": False,
            "error": "Checkpoint system not initialized",
        }

    try:
        diff_text = _checkpoint_manager.diff(checkpoint_id)

        return {
            "success": True,
            "checkpoint_id": checkpoint_id,
            "diff": diff_text,
        }

    except Exception as e:
        logger.error(f"Error getting diff: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def enter_tangent_mode(
    conversation_history: List[Dict] | None = None,
) -> Dict[str, Any]:
    """
    Enter tangent mode to explore an idea without affecting the main conversation.

    Use this when you want to explore a tangential topic or try an experimental
    approach without losing the current conversation context.

    Args:
        conversation_history: Current conversation history to checkpoint

    Returns:
        dict: Status of tangent mode entry

    Example:
        >>> result = enter_tangent_mode(conversation_history)
        >>> # Now explore a tangent...
        >>> # Later, exit to restore original conversation
    """
    if not _tangent_manager:
        return {
            "success": False,
            "error": "Tangent system not initialized",
        }

    try:
        _tangent_manager.enter(conversation_history or [])

        return {
            "success": True,
            "in_tangent": True,
            "message": "↯ Entered tangent mode. Conversation checkpointed.",
        }

    except Exception as e:
        logger.error(f"Error entering tangent: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def exit_tangent_mode(
    keep_tail: bool = False, conversation_history: List[Dict] | None = None
) -> Dict[str, Any]:
    """
    Exit tangent mode and optionally restore the original conversation.

    Args:
        keep_tail: If True, keeps the last Q&A pair from the tangent
                  If False (default), restores original conversation entirely

    Returns:
        dict: Restored conversation history

    Example:
        >>> result = exit_tangent_mode(keep_tail=True)
        >>> # Original conversation restored, with last tangent Q&A kept
    """
    if not _tangent_manager:
        return {
            "success": False,
            "error": "Tangent system not initialized",
        }

    try:
        current_history = conversation_history or []
        restored, status = _tangent_manager.exit(current_history, keep_tail=keep_tail)

        return {
            "success": True,
            "in_tangent": False,
            "restored_conversation": restored,
            "kept_tail": keep_tail,
            "message": status,
        }

    except Exception as e:
        logger.error(f"Error exiting tangent: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def forget_messages(
    count: int, conversation_history: List[Dict] | None = None
) -> Dict[str, Any]:
    """Remove recent messages from the conversation history."""
    if not _tangent_manager:
        return {
            "success": False,
            "error": "Tangent system not initialized",
        }

    try:
        current_history = conversation_history or []
        previous_user_messages = sum(
            1 for msg in current_history if msg.get("role") == "user"
        )
        new_history, status = _tangent_manager.forget(current_history, count=count)
        remaining_user_messages = sum(
            1 for msg in new_history if msg.get("role") == "user"
        )
        removed_user_messages = previous_user_messages - remaining_user_messages

        return {
            "success": True,
            "messages_removed": removed_user_messages,
            "messages_trimmed": len(current_history) - len(new_history),
            "remaining_messages": len(new_history),
            "new_history": new_history,
            "message": status,
        }

    except Exception as e:
        logger.error(f"Error forgetting messages: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


def get_context_usage() -> Dict[str, Any]:
    """
    Get current context window usage information.

    Use this to monitor how much of the LLM's context window is being used.
    This helps decide when to compact context or create checkpoints.

    Returns:
        dict: Context usage information with percentage and recommendation

    Example:
        >>> result = get_context_usage()
        >>> if result['percentage'] > 80:
        ...     print("Consider compacting context or creating checkpoint")
    """
    try:
        # Default values - in real implementation these come from the LLM tracker
        tokens_used = 0
        max_tokens = 128000  # Default for most models

        try:
            from aura_cli.core.stats import get_stats

            stats = get_stats()
            tokens_used = getattr(stats, "total_tokens", 0)
        except Exception as _e:
            logger.debug(f"Ignorado: {_e}")

        percentage = get_context_percentage(tokens_used, max_tokens)
        should_compact = should_compact_context(tokens_used, max_tokens)

        recommendation = "Context usage is healthy."
        if percentage >= 90:
            recommendation = (
                "⚠️ CRITICAL: Context nearly full. Create checkpoint and compact NOW."
            )
        elif percentage >= 75:
            recommendation = "⚠️ WARNING: Consider creating a checkpoint soon."
        elif percentage >= 50:
            recommendation = "Context usage is moderate. Continue normally."

        return {
            "success": True,
            "tokens_used": tokens_used,
            "max_tokens": max_tokens,
            "percentage": round(percentage, 1),
            "should_compact": should_compact,
            "recommendation": recommendation,
        }

    except Exception as e:
        logger.error(f"Error getting context usage: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


CHECKPOINT_TOOLS = {
    "create_checkpoint": create_checkpoint,
    "list_checkpoints": list_checkpoints,
    "restore_checkpoint": restore_checkpoint,
    "diff_checkpoint": diff_checkpoint,
    "enter_tangent_mode": enter_tangent_mode,
    "exit_tangent_mode": exit_tangent_mode,
    "forget_messages": forget_messages,
    "get_context_usage": get_context_usage,
}


def get_checkpoint_tool_schemas() -> List[Dict[str, Any]]:
    """Get OpenAI-compatible tool schemas for checkpoint tools."""
    return [
        {
            "type": "function",
            "function": {
                "name": "create_checkpoint",
                "description": "Create a checkpoint of the current project state before making significant changes. Returns checkpoint ID.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Brief description of what the checkpoint captures",
                        }
                    },
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_checkpoints",
                "description": "List all available checkpoints that can be restored.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "restore_checkpoint",
                "description": "Restore project state to a previous checkpoint. Use this to undo changes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "checkpoint_id": {
                            "type": "string",
                            "description": "The ID of the checkpoint to restore",
                        },
                        "hard": {
                            "type": "boolean",
                            "description": "If true, also remove files created after the checkpoint",
                            "default": False,
                        },
                    },
                    "required": ["checkpoint_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "diff_checkpoint",
                "description": "Show differences between current state and a checkpoint.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "checkpoint_id": {
                            "type": "string",
                            "description": "The ID of the checkpoint to compare against",
                        },
                    },
                    "required": ["checkpoint_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_context_usage",
                "description": "Get current context window usage. Use to decide when to compact context or create checkpoints.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    ]
