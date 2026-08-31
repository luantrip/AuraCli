"""ADK bridge initialization state contracts."""

import os
import threading
from unittest.mock import Mock, patch

from aura_cli.core import agents


def test_feature_flag_is_evaluated_at_call_time() -> None:
    with patch.dict(os.environ, {"AURA_USE_ADK_BRIDGE": "false"}):
        assert agents.is_adk_bridge_enabled() is False
    with patch.dict(os.environ, {"AURA_USE_ADK_BRIDGE": "true"}):
        assert agents.is_adk_bridge_enabled() is True


def test_worker_access_does_not_publish_permanent_stub() -> None:
    original = (
        agents._adk_bridge_loaded,
        agents.ADKAgentAdapter,
        agents.ADKBridgeFactory,
        agents.ADKConfigAdapter,
        agents.ADKResponseAdapter,
    )
    agents._adk_bridge_loaded = False
    agents.ADKAgentAdapter = None
    agents.ADKBridgeFactory = None
    agents.ADKConfigAdapter = None
    agents.ADKResponseAdapter = None
    worker = Mock(name="agi-worker")

    try:
        with (
            patch.object(agents.threading, "current_thread", return_value=worker),
            patch.object(
                agents.threading, "main_thread", return_value=Mock(name="main-thread")
            ),
            patch.object(agents.threading, "active_count", return_value=2),
        ):
            assert agents._ensure_adk_bridge() is False

        assert agents._adk_bridge_loaded is False
        assert agents.ADKBridgeFactory is None
    finally:
        (
            agents._adk_bridge_loaded,
            agents.ADKAgentAdapter,
            agents.ADKBridgeFactory,
            agents.ADKConfigAdapter,
            agents.ADKResponseAdapter,
        ) = original


def test_main_thread_preload_is_reused_by_worker_thread() -> None:
    original = (
        agents._adk_bridge_loaded,
        agents._main_thread_id,
        agents.ADKAgentAdapter,
        agents.ADKBridgeFactory,
        agents.ADKConfigAdapter,
        agents.ADKResponseAdapter,
    )
    agents._adk_bridge_loaded = False
    agents._main_thread_id = None
    agents.ADKAgentAdapter = None
    agents.ADKBridgeFactory = None
    agents.ADKConfigAdapter = None
    agents.ADKResponseAdapter = None
    results: list[bool] = []

    try:
        assert agents._ensure_adk_bridge() is True
        worker = threading.Thread(
            target=lambda: results.append(agents._ensure_adk_bridge())
        )
        worker.start()
        worker.join(timeout=5)
        assert not worker.is_alive()
        assert results == [True]
    finally:
        (
            agents._adk_bridge_loaded,
            agents._main_thread_id,
            agents.ADKAgentAdapter,
            agents.ADKBridgeFactory,
            agents.ADKConfigAdapter,
            agents.ADKResponseAdapter,
        ) = original
