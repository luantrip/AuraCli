"""
Testes para OpsAgent no ADK.

Valida que:
1. OpsAgent existe no ADK
2. OpsAgent está registrado no Bridge
3. ops_worker.py usa ADK Bridge
4. Fallback funciona
"""

from pathlib import Path

import pytest


def test_ops_agent_exists_in_adk():
    """Verifica que OpsAgent existe no ADK."""
    from aura_cli.adk.specialized import OpsAgent

    assert OpsAgent is not None
    assert hasattr(OpsAgent, "execute")


def test_ops_agent_registration_falls_back_without_adk():
    """O registro nativo completo é verificável sem ADK ou provider."""
    import logging

    from aura_cli.application.agents.ops_execution import get_ops_agent_specs
    from aura_cli.cli.workers.ops_agent_registration import register_ops_agents

    class FakeOrchestrator:
        def __init__(self):
            self.agents = []
            self.context = {}

        def register_agent(self, agent):
            self.agents.append(agent)

    orchestrator = FakeOrchestrator()
    outcome = register_ops_agents(
        orchestrator=orchestrator,
        communication_manager=None,
        agent_memory=None,
        model="offline/test-model",
        use_adk=False,
        logger=logging.getLogger(__name__),
    )

    expected_ids = tuple(spec.agent_id for spec in get_ops_agent_specs())
    assert outcome.backend == "native"
    assert outcome.agent_ids == expected_ids
    assert len(orchestrator.agents) == len(expected_ids)


def test_ops_worker_has_feature_flag():
    """Verifica que ops_worker tem feature flag."""
    from aura_cli.cli.workers import ops_worker

    assert hasattr(ops_worker, "USE_ADK_BRIDGE")
    assert isinstance(ops_worker.USE_ADK_BRIDGE, bool)


def test_ops_worker_imports_adk_bridge():
    """Verifica que ops_worker importa ADK Bridge."""
    source = Path("aura_cli/cli/workers/ops_worker.py").read_text()

    assert "register_ops_agents" in source
    assert "USE_ADK_BRIDGE" in source


def test_ops_worker_has_fallback():
    """Verifica que o adapter Ops mantém fallback para agentes nativos."""
    worker_source = Path("aura_cli/cli/workers/ops_worker.py").read_text()
    adapter_source = Path("aura_cli/cli/workers/ops_agent_registration.py").read_text()

    assert "register_ops_agents" in worker_source
    assert "create_adk_wrapper" in adapter_source
    assert "OpsCodeAgent" in adapter_source


def test_ops_worker_syntax_valid():
    """Verifica que ops_worker tem sintaxe válida."""
    import ast

    source = Path("aura_cli/cli/workers/ops_worker.py").read_text()

    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"Erro de sintaxe: {e}")


def test_adk_bridge_status_is_explicit_without_skipping():
    """A disponibilidade opcional do ADK é observável como estado, não skip."""
    import aura_cli.core.agents as agents

    loaded = agents._ensure_adk_bridge()
    factory = agents.ADKBridgeFactory
    registered = factory.list_registered() if factory is not None else []

    assert isinstance(loaded, bool)
    assert isinstance(registered, list)
    assert agents.is_adk_available() is (factory is not None and loaded)
    if not agents.is_adk_available():
        assert registered == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
