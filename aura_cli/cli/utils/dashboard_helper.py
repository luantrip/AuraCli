"""
Dashboard Helper Module.

This module provides shared utilities for starting and managing the real-time agent dashboard
across different worker types (AgiWorker, OpsWorker).
"""

import logging
import time
from typing import Any, Callable
import uuid

from aura_cli.cli.ui.advanced.agent_dashboard import AgentOrchestrationView
from aura_cli.cli.utils.thread_manager import get_thread_manager


def start_dashboard_thread(
    worker: Any,
    orchestrator: Any,
    message_callback: Callable[[str], None],
    logger: logging.Logger,
    prefix: str = "Aura AGI",
    headless: bool = False,
    use_advanced_features: bool = True,
    task_id: str = "unknown",
) -> None:
    """
    Starts the real-time dashboard in a separate thread.

    Args:
        worker: The worker instance (must accept dashboard_active/dashboard_thread attributes)
        orchestrator: The AgentOrchestrator instance
        message_callback: Function to call for sending status updates (e.g. queue.put or adapter.emit)
        logger: Logger instance for logging errors
        prefix: Prefix for status messages (e.g. "Aura AGI", "Aura Ops")
        headless: If True, does not start dashboard
        use_advanced_features: If False, does not start dashboard
        task_id: Task ID for thread naming uniqueness
    """
    if headless or not use_advanced_features:
        return

    # Use LiveDashboard when orchestrator is not available
    if not orchestrator:
        try:
            from aura_cli.cli.ui.live_dashboard import LiveAgentDashboard

            q = getattr(worker, "status_queue", None)
            dashboard = LiveAgentDashboard(prefix, q)
            dashboard.start()
            worker.dashboard_active = True
            worker.live_dashboard = dashboard
        except Exception as e:
            logger.debug(f"LiveDashboard skipped: {e}")
        return

    def dashboard_loop():
        """Real-time dashboard loop."""
        # Initialize the TUI view
        AgentOrchestrationView(orchestrator)
        worker.dashboard_active = True

        try:
            last_update = 0
            last_message = ""
            while getattr(worker, "dashboard_active", False):
                current_time = time.time()
                if current_time - last_update >= 2.0:
                    try:
                        status = orchestrator.get_status()
                        agents_count = len(status.get("agents", {}))

                        new_message = (
                            f"› [{prefix}] Status: {agents_count} agentes ativos"
                        )
                        if new_message != last_message and agents_count > 0:
                            message_callback(new_message)
                            last_message = new_message

                        last_update = current_time
                    except (AttributeError, KeyError) as e:
                        logger.debug(f"Error updating dashboard (attribute/key): {e}")
                    except Exception as e:
                        logger.warning(
                            f"Unexpected error updating dashboard: {e}", exc_info=True
                        )

                time.sleep(1.0)
        except (AttributeError, RuntimeError) as e:
            logger.debug(f"Dashboard terminated (attribute/runtime): {e}")
        except Exception as e:
            logger.warning(f"Unexpected error in dashboard: {e}", exc_info=True)
        finally:
            worker.dashboard_active = False

    thread_manager = get_thread_manager()
    # Use unique name to avoid collisions when multiple workers run
    thread_name = (
        f"{prefix.lower().replace(' ', '_')}_dashboard_{task_id}_{uuid.uuid4().hex[:8]}"
    )

    # Check if thread is already running
    current_thread = getattr(worker, "dashboard_thread", None)
    if current_thread and current_thread.is_alive():
        logger.debug(f"Dashboard thread already running: {current_thread.name}")
        return

    try:
        new_thread = thread_manager.register_thread(
            name=thread_name,
            target=dashboard_loop,
            daemon=True,
            shutdown_timeout=5.0,
        )
        worker.dashboard_thread = new_thread
        logger.info(f"Real-time dashboard started for {prefix}")
    except Exception as e:
        logger.warning(f"Failed to start dashboard thread: {e}")
