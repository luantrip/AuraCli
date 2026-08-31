"""ADK-owned bootstrap for the neutral application agent registry."""

from __future__ import annotations

import threading

from aura_cli.application.agents import AgentRegistry

_ready = False
_lock = threading.Lock()


def ensure_adk_agents_registered() -> None:
    """Register built-in ADK agents once, from the main thread."""
    global _ready
    with _lock:
        if _ready:
            return
        if threading.current_thread() is not threading.main_thread():
            return

        from aura_cli.adk.specialized import (
            CodeAgent,
            OpsAgent,
            RefactorAgent,
            ReviewAgent,
            TestAgent,
        )

        AgentRegistry.register("code", CodeAgent)
        AgentRegistry.register("ops", OpsAgent)
        AgentRegistry.register("refactor", RefactorAgent)
        AgentRegistry.register("review", ReviewAgent)
        AgentRegistry.register("test", TestAgent)
        _ready = True


def registered_adk_agents() -> list[str]:
    ensure_adk_agents_registered()
    return AgentRegistry.names()
