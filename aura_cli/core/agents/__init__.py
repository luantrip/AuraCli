"""
Agent abstraction system.

Provides the core agent infrastructure:
    - AgentBackend / NativeBackend: Backend interface and native implementation
    - AgentMetrics: Performance metrics per agent
    - CheckpointableWorkflow: Workflows with checkpoint support
    - ADK Bridge: Thread-safe lazy-loaded bridge to the ADK framework

Thread Safety:
    ADK Bridge components are lazily loaded to avoid PyArrow thread-safety issues.
    Call `_ensure_adk_bridge()` or `ADKBridgeFactory.ensure_registered()` from
    the main thread before starting worker threads.
"""

from __future__ import annotations

import logging
import os
import threading
from typing import TYPE_CHECKING, Optional, Type

if TYPE_CHECKING:
    from .adk_bridge import (
        ADKAgentAdapter as ADKAgentAdapterType,
    )
    from .adk_bridge import (
        ADKBridgeFactory as ADKBridgeFactoryType,
    )
    from .adk_bridge import (
        ADKConfigAdapter as ADKConfigAdapterType,
    )
    from .adk_bridge import (
        ADKResponseAdapter as ADKResponseAdapterType,
    )

logger = logging.getLogger(__name__)

# Thread-safe lazy loading for ADK bridge
_adk_bridge_loaded = False
_adk_bridge_lock = threading.Lock()
_main_thread_id: Optional[int] = None

ADKAgentAdapter: Optional[Type[ADKAgentAdapterType]] = None
ADKBridgeFactory: Optional[Type[ADKBridgeFactoryType]] = None
ADKConfigAdapter: Optional[Type[ADKConfigAdapterType]] = None
ADKResponseAdapter: Optional[Type[ADKResponseAdapterType]] = None


def is_adk_bridge_enabled() -> bool:
    """Return the current process policy for ADK bridge usage."""
    return os.getenv("AURA_USE_ADK_BRIDGE", "true").lower() == "true"


class _ADKNotAvailableError(RuntimeError):
    """Raised when ADK Bridge is accessed from a worker thread without prior initialization."""


class _StubADKBridgeFactory:
    """Stub factory for worker threads when ADK was not pre-registered."""

    @classmethod
    def create_adapter(cls, *args, **kwargs):
        """Create and return an agent adapter by name."""
        raise _ADKNotAvailableError(
            "ADK Bridge cannot be used in worker threads. "
            "Call ADKBridgeFactory.ensure_registered() in the main thread before starting workers."
        )

    @classmethod
    def ensure_registered(cls) -> None:
        """No-op in stub - registration must happen in main thread."""
        logger.warning("ensure_registered() called on stub - ADK not available")

    @classmethod
    def list_registered(cls) -> list:
        """Return list of registered agent adapter names."""
        return []

    @classmethod
    def register(cls, *args, **kwargs) -> None:
        """Register a new agent adapter factory."""
        raise _ADKNotAvailableError("Cannot register agents from worker thread")


def _ensure_adk_bridge() -> bool:
    """
    Ensure ADK bridge components are loaded (thread-safe).

    This function must be called from the main thread to properly initialize
    PyArrow and other dependencies that are not thread-safe during initialization.

    Returns:
        True if ADK bridge was loaded successfully, False otherwise.

    Note:
        If called from a worker thread before main thread initialization,
        initialization is deferred without publishing a permanent stub.
    """
    global _adk_bridge_loaded, _main_thread_id
    global ADKAgentAdapter, ADKBridgeFactory, ADKConfigAdapter, ADKResponseAdapter

    if _adk_bridge_loaded:
        return (
            ADKBridgeFactory is not None
            and ADKBridgeFactory is not _StubADKBridgeFactory
        )

    with _adk_bridge_lock:
        if _adk_bridge_loaded:
            return (
                ADKBridgeFactory is not None
                and ADKBridgeFactory is not _StubADKBridgeFactory
            )

        current_thread = threading.current_thread()
        is_main_thread = (
            current_thread is threading.main_thread()
            or current_thread.name == "MainThread"
            or (
                hasattr(threading, "main_thread")
                and current_thread is threading.main_thread()
            )
        )

        if not is_main_thread:
            logger.warning(
                f"ADK Bridge accessed from worker thread '{current_thread.name}' "
                "before main thread initialization. Initialization deferred."
            )
            return False

        _main_thread_id = current_thread.ident

        try:
            from .adk_bridge import (
                ADKAgentAdapter as _ADKAgentAdapter,
            )
            from .adk_bridge import (
                ADKBridgeFactory as _ADKBridgeFactory,
            )
            from .adk_bridge import (
                ADKConfigAdapter as _ADKConfigAdapter,
            )
            from .adk_bridge import (
                ADKResponseAdapter as _ADKResponseAdapter,
            )

            ADKAgentAdapter = _ADKAgentAdapter
            ADKBridgeFactory = _ADKBridgeFactory
            ADKConfigAdapter = _ADKConfigAdapter
            ADKResponseAdapter = _ADKResponseAdapter
            _adk_bridge_loaded = True
            logger.debug("ADK Bridge loaded successfully in main thread")
            return True

        except ImportError as e:
            logger.warning(f"Could not import ADK Bridge: {e}")
            ADKAgentAdapter = None
            ADKBridgeFactory = _StubADKBridgeFactory  # type: ignore
            ADKConfigAdapter = None
            ADKResponseAdapter = None
            _adk_bridge_loaded = True
            return False
        except Exception as e:
            logger.error(f"Error loading ADK Bridge: {e}", exc_info=True)
            ADKAgentAdapter = None
            ADKBridgeFactory = _StubADKBridgeFactory  # type: ignore
            ADKConfigAdapter = None
            ADKResponseAdapter = None
            _adk_bridge_loaded = True
            return False


def is_adk_available() -> bool:
    """Check if ADK Bridge is available and properly initialized."""
    if not _adk_bridge_loaded:
        return False
    if ADKBridgeFactory is None:
        return False
    if ADKBridgeFactory is _StubADKBridgeFactory:
        return False
    try:
        if hasattr(ADKBridgeFactory, "list_registered") and hasattr(
            ADKBridgeFactory, "create_adapter"
        ):
            ADKBridgeFactory.list_registered()
            return True
    except (RuntimeError, AttributeError):
        return False
    except (TypeError, ValueError) as e:
        import logging

        logging.getLogger(__name__).debug(
            f"ADK factory check: unexpected error (assuming real): {e}"
        )
        return True
    return False


def ensure_adk_initialized() -> bool:
    """
    Ensure ADK is fully initialized and agents are registered.

    This is a convenience function that:
    1. Ensures ADK bridge is loaded
    2. Ensures agents are registered

    Returns:
        True if ADK is fully initialized, False otherwise.
    """
    if not _ensure_adk_bridge():
        logger.warning("ADK bridge could not be loaded")
        return False

    if ADKBridgeFactory is None:
        logger.warning("ADKBridgeFactory is None after loading bridge")
        return False

    if ADKBridgeFactory is _StubADKBridgeFactory:
        logger.debug("ADKBridgeFactory is stub - ADK not available in this thread")
        return False

    try:
        ADKBridgeFactory.ensure_registered()
        registered = ADKBridgeFactory.list_registered()
        if registered:
            logger.debug(f"ADK agents registered: {registered}")
            return True
        else:
            logger.warning("No ADK agents registered")
            return False
    except (RuntimeError, AttributeError, TypeError, ValueError) as e:
        logger.warning(
            f"Failed to ensure ADK agents are registered: {e}", exc_info=True
        )
        return False
    except Exception as e:
        logger.error(f"Unexpected error ensuring ADK registration: {e}", exc_info=True)
        raise


from .agent_metrics import (
    AgentExecutionMetrics,
    AgentMetrics,
    AgentMetricsRepository,
    MetricsCollector,
    get_metrics_collector,
)
from .factory import AgentBackendFactory
from .interface import AgentBackend, AgentConfig, AgentResponse
from .native_backend import NativeBackend

# ADK Wrapper (lazy import to avoid circular dependencies)
try:
    from .adk_integration import create_adk_wrapper
    from .adk_wrapper import ADKAgentWrapper
except ImportError:
    ADKAgentWrapper = None  # type: ignore[assignment,misc]
    create_adk_wrapper = None  # type: ignore[assignment]

__all__ = [
    "ADKAgentAdapter",
    "ADKAgentWrapper",
    "ADKBridgeFactory",
    "ADKConfigAdapter",
    "ADKResponseAdapter",
    "AgentBackend",
    "AgentBackendFactory",
    "AgentConfig",
    "AgentExecutionMetrics",
    "AgentMetrics",
    "AgentMetricsRepository",
    "AgentResponse",
    "MetricsCollector",
    "NativeBackend",
    "create_adk_wrapper",
    "ensure_adk_initialized",
    "get_metrics_collector",
    "is_adk_available",
    "is_adk_bridge_enabled",
]
