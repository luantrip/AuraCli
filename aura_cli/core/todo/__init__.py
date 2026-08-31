"""
Task management (TODO) module for Aura CLI.

Provides functionality for:
- Task tracking from .aura/to-do.md file
- Progress notifications
- Visual task interface
"""

from aura_cli.core.todo.todo_notifications import (
    check_and_notify_task_completion,
    get_todo_progress_message,
    send_todo_notification_to_queue,
)
from aura_cli.core.todo.todo_tracker import (
    TodoTask,
    TodoTracker,
    get_todo_tracker,
    refresh_todo_tracker,
)

__all__ = [
    "TodoTask",
    "TodoTracker",
    "check_and_notify_task_completion",
    "get_todo_progress_message",
    "get_todo_tracker",
    "refresh_todo_tracker",
    "send_todo_notification_to_queue",
]
