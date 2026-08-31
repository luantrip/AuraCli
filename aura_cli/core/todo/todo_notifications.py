"""To-do task completion notifications via the status_queue.

Sends formatted notifications when tasks are marked done and exposes a
progress message helper. Compares previous vs current done count to detect
new completions. Task previews are capped at 50 characters.
"""

from __future__ import annotations

import queue
from typing import Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.todo.todo_tracker import TodoTracker, get_todo_tracker

logger = get_logger(__name__)


def send_todo_notification_to_queue(
    status_queue: queue.Queue[str],
    task_text: str,
    tracker: Optional[TodoTracker] = None,
) -> None:
    """Send a completed-task notification to the status queue."""
    if tracker is None:
        tracker = get_todo_tracker()

    stats = tracker.get_stats()
    total = stats["total"]
    done = stats["done"]
    percentage = int(done / total * 100) if total > 0 else 0

    notification = (
        f"› [To-do] + Task completed: {task_text} ({done}/{total}, {percentage}%)"
    )
    status_queue.put(notification)


def check_and_notify_task_completion(
    status_queue: queue.Queue[str],
    previous_done_count: int,
    tracker: Optional[TodoTracker] = None,
) -> int:
    """Check for newly completed tasks and send notifications."""
    if tracker is None:
        tracker = get_todo_tracker()

    tracker.refresh()
    stats = tracker.get_stats()
    current_done_count = stats["done"]

    if current_done_count > previous_done_count:
        done_tasks = tracker.get_done_tasks()
        if done_tasks:
            latest_task = done_tasks[-1]
            send_todo_notification_to_queue(status_queue, latest_task.text, tracker)

    return current_done_count


def get_todo_progress_message(tracker: Optional[TodoTracker] = None) -> str:
    """Return a formatted progress message for the status queue."""
    if tracker is None:
        tracker = get_todo_tracker()

    stats = tracker.get_stats()
    total = stats["total"]
    done = stats["done"]

    if total == 0:
        return ""

    percentage = int(done / total * 100) if total > 0 else 0
    current_task = tracker.get_current_task()

    if current_task:
        task_preview = (
            current_task.text[:50] + "..."
            if len(current_task.text) > 50
            else current_task.text
        )
        return f"› [To-do] Working on: {task_preview} ({done}/{total}, {percentage}%)"
    else:
        return f"› [To-do] Progress: {done}/{total} tasks ({percentage}%)"
