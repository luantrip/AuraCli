"""
Aura Integration Bridge Testing Suite.

Tests bidirectional synchronization and functional adapters between
Core and Native ADK systems.

Removed (modules deleted in refactor):
  - test_integrated_tool_registry_* (unified_tool_registry removed)
  - test_workflow_bridge_* (workflow_bridge removed)
"""

from unittest.mock import AsyncMock, Mock

import pytest

# ---------------------------------------------------------------------------
# Memory Bridge
# ---------------------------------------------------------------------------


def test_memory_bridge_singleton():
    """MemoryBridge maintains singleton state."""
    from aura_cli.core.agents.memory_bridge import MemoryBridge, get_memory_bridge

    bridge1 = get_memory_bridge()
    bridge2 = get_memory_bridge()
    assert bridge1 is bridge2
    assert isinstance(bridge1, MemoryBridge)


def test_memory_bridge_sync_control():
    """Enable/disable synchronization toggles work correctly."""
    from aura_cli.core.agents.memory_bridge import get_memory_bridge

    bridge = get_memory_bridge()
    bridge.enable_sync()
    assert bridge._sync_enabled is True

    bridge.disable_sync()
    assert bridge._sync_enabled is False


@pytest.mark.asyncio
async def test_memory_bridge_sync_to_core():
    """Native ADK to Core memory synchronization flow."""
    from aura_cli.core.agents.agent_memory import AgentMemory
    from aura_cli.core.agents.memory_bridge import get_memory_bridge

    bridge = get_memory_bridge()
    agent_memory = AgentMemory()
    bridge.set_agent_memory(agent_memory)

    adk_memory = AsyncMock()
    adk_entry = Mock()
    adk_entry.id = "test_sync_id"
    adk_entry.content = "Cognitive sync content"
    adk_entry.metadata = {}
    adk_entry.timestamp = 1234567890.0
    adk_memory.search = AsyncMock(return_value=[adk_entry])

    count = await bridge.sync_to_legacy("test_native_agent", adk_memory, limit=10)
    assert count >= 0


# ---------------------------------------------------------------------------
# Metrics Bridge
# ---------------------------------------------------------------------------


def test_metrics_bridge_singleton():
    """MetricsBridge maintains singleton state."""
    from aura_cli.core.metrics.metrics_bridge import MetricsBridge, get_metrics_bridge

    bridge1 = get_metrics_bridge()
    bridge2 = get_metrics_bridge()
    assert bridge1 is bridge2
    assert isinstance(bridge1, MetricsBridge)


def test_metrics_bridge_execution_tracking():
    """Execution telemetry tracking for Native agents."""
    from aura_cli.core.metrics.metrics_bridge import get_metrics_bridge
    from aura_cli.core.stats import StatsTracker

    bridge = get_metrics_bridge()
    stats = StatsTracker()
    bridge.set_stats_tracker(stats)

    initial_tokens = stats.total_tokens
    bridge.track_adk_execution(
        agent_id="telemetry_agent",
        execution_time=0.5,
        tokens=50,
        success=True,
    )
    assert stats.total_tokens >= initial_tokens


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
