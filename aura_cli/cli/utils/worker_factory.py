"""Factory functions for creating and registering worker threads.

This module provides centralized factory functions for creating AgiWorker and
OpsWorker instances and registering them with the ThreadManager. This eliminates
code duplication across multiple modules (helpers.py, command_processor.py, etc.).

Functions:
    create_agi_worker_thread: Create and register an AgiWorker thread
    create_ops_worker_thread: Create and register an OpsWorker thread
"""

from pathlib import Path
import threading
from typing import TYPE_CHECKING, Dict, Optional, Tuple
import uuid

from aura_cli.cli.ops_tools_map import get_ops_tools_for_mode
from aura_cli.cli.utils.thread_manager import get_thread_manager
from aura_cli.cli.utils.worker_readiness import ensure_worker_ready
from aura_cli.core.events.event_bus import get_event_bus
from aura_cli.core.service_registry import get_tools_dict

if TYPE_CHECKING:
    from aura_cli.cli.workers import AgiWorker, OpsWorker


def create_agi_worker_thread(
    objective: str,
    model: str,
    api_keys: Dict[str, str],
    headless: bool = False,
    project_root: Optional[Path] = None,
    delegation_payload: Optional[Dict[str, object]] = None,
    shutdown_timeout: float = 30.0,
    enable_adversarial_validation: bool = False,
) -> Tuple["AgiWorker", threading.Thread]:
    """Create and register an AgiWorker thread.

    Args:
        objective: Task objective for the AGI worker
        model: LLM model name to use
        api_keys: Dictionary of API keys
        headless: Whether to run in headless mode
        project_root: Optional project root path
        delegation_payload: Optional structured handoff payload from chat delegation
        shutdown_timeout: Timeout for thread shutdown
        enable_adversarial_validation: If True, run TesterWorker after code generation

    Returns:
        Tuple of (AgiWorker instance, registered Thread)
    """
    from aura_cli.cli.workers import AgiWorker
    from aura_cli.core.agents import is_adk_bridge_enabled

    if is_adk_bridge_enabled():
        try:
            from aura_cli.adk.registry import ensure_adk_agents_registered

            ensure_adk_agents_registered()
        except (ImportError, AttributeError) as _e:
            pass  # silenced: {_e}
        except Exception as _e:
            pass  # silenced: {_e}

    ensure_worker_ready(
        worker_type="agi",
        model=model,
        api_keys=api_keys,
        project_root=project_root,
        dependency_check=lambda: (get_tools_dict(), None)[1],
    )

    status_queue = get_event_bus().get_queue()
    available_tools = get_tools_dict()

    agi_worker = AgiWorker(
        objective,
        model,
        api_keys,
        headless=headless,
        status_queue=status_queue,
        available_tools=available_tools,
        project_root=project_root,
        delegation_payload=delegation_payload,
        enable_adversarial_validation=enable_adversarial_validation,
    )

    thread_manager = get_thread_manager()
    # Use UUID for truly unique thread names to avoid collisions
    thread_name = f"agi_worker_{uuid.uuid4().hex[:16]}"

    # Register and start the thread
    registered_thread = thread_manager.register_thread(
        name=thread_name,
        target=agi_worker.run,
        daemon=True,
        shutdown_timeout=shutdown_timeout,
        stop_callback=agi_worker.cleanup,
    )

    return agi_worker, registered_thread


def create_ops_worker_thread(
    task: str,
    model: str,
    api_keys: Dict[str, str],
    mode: str = "general",
    headless: bool = False,
    project_root: Optional[Path] = None,
    delegation_payload: Optional[Dict[str, object]] = None,
    shutdown_timeout: float = 30.0,
) -> Tuple["OpsWorker", threading.Thread]:
    """Create and register an OpsWorker thread.

    Args:
        task: Task description for the Ops worker
        model: LLM model name to use
        api_keys: Dictionary of API keys
        mode: Ops mode ('git', 'docker', or 'general')
        headless: Whether to run in headless mode
        project_root: Optional project root path
        delegation_payload: Optional structured handoff payload from chat delegation
        shutdown_timeout: Timeout for thread shutdown

    Returns:
        Tuple of (OpsWorker instance, registered Thread)
    """
    from aura_cli.cli.workers import OpsWorker

    ensure_worker_ready(
        worker_type="ops",
        model=model,
        api_keys=api_keys,
        project_root=project_root,
        dependency_check=lambda: (get_ops_tools_for_mode(mode), None)[1],
    )

    status_queue = get_event_bus().get_queue()

    ops_worker = OpsWorker(
        task,
        model,
        api_keys,
        mode=mode,
        headless=headless,
        status_queue=status_queue,
        ops_tools=get_ops_tools_for_mode(mode),
        project_root=project_root,
        delegation_payload=delegation_payload,
    )

    thread_manager = get_thread_manager()
    thread_name = f"ops_worker_{uuid.uuid4().hex[:16]}"
    registered_thread = thread_manager.register_thread(
        name=thread_name,
        target=ops_worker.run,
        daemon=True,
        shutdown_timeout=shutdown_timeout,
        stop_callback=ops_worker.cleanup,
    )

    return ops_worker, registered_thread
