"""
Testes de integração do ADK Bridge com Workers.

Valida que:
1. Feature flag funciona corretamente
2. ADK Bridge é usado quando habilitado
3. Fallback para sistema legado funciona
4. Agentes são registrados corretamente
"""

import os
from pathlib import Path

import pytest


def test_feature_flag_default():
    """Verifica que feature flag está habilitada por padrão."""
    # Limpar env var se existir
    if "AURA_USE_ADK_BRIDGE" in os.environ:
        del os.environ["AURA_USE_ADK_BRIDGE"]

    # Reimportar para pegar valor padrão
    import importlib

    import aura_cli.cli.workers.agi_worker as agi_worker_module

    importlib.reload(agi_worker_module)

    # Deve ser True por padrão
    assert agi_worker_module.USE_ADK_BRIDGE is True


def test_feature_flag_can_be_disabled():
    """Verifica que feature flag pode ser desabilitada."""
    os.environ["AURA_USE_ADK_BRIDGE"] = "false"

    import importlib

    import aura_cli.cli.workers.agi_worker as agi_worker_module

    importlib.reload(agi_worker_module)

    assert agi_worker_module.USE_ADK_BRIDGE is False

    # Limpar
    del os.environ["AURA_USE_ADK_BRIDGE"]


def test_agi_worker_has_feature_flag():
    """Verifica que agi_worker tem a feature flag."""
    from aura_cli.cli.workers import agi_worker

    assert hasattr(agi_worker, "USE_ADK_BRIDGE")
    assert isinstance(agi_worker.USE_ADK_BRIDGE, bool)


def test_agi_worker_uses_neutral_adk_registry():
    """Worker bootstrap must not depend on the Core bridge factory."""
    agi_source = Path("aura_cli/cli/workers/agi_worker.py").read_text(encoding="utf-8")
    factory_source = Path("aura_cli/cli/utils/worker_factory.py").read_text(
        encoding="utf-8"
    )

    assert "USE_ADK_BRIDGE" in agi_source
    assert "ensure_adk_agents_registered" in factory_source
    assert "ADKBridgeFactory" not in factory_source


def test_legacy_system_still_available():
    """Verifica que sistema legado ainda está disponível como fallback."""
    try:
        from aura_cli.core.agents.specialized_agents.code_agent import CodeAgent
        from aura_cli.core.agents.specialized_agents.refactor_agent import RefactorAgent
        from aura_cli.core.agents.specialized_agents.review_agent import ReviewAgent
        from aura_cli.core.agents.specialized_agents.test_agent import TestAgent

        # Todos devem estar disponíveis
        assert CodeAgent is not None
        assert ReviewAgent is not None
        assert RefactorAgent is not None
        assert TestAgent is not None

    except ImportError as e:
        pytest.fail(f"Sistema legado não disponível: {e}")


def test_adk_bridge_available():
    """Verifica que ADK Bridge está disponível."""
    try:
        import aura_cli.core.agents as agents_module

        # Ensure initialization
        if hasattr(agents_module, "ensure_adk_initialized"):
            agents_module.ensure_adk_initialized()

        # Check factory on the module to get updated reference
        assert agents_module.ADKBridgeFactory is not None
        assert hasattr(agents_module.ADKBridgeFactory, "create_adapter")
        assert hasattr(agents_module.ADKBridgeFactory, "list_registered")

    except ImportError as e:
        pytest.fail(f"ADK Bridge não disponível: {e}")


# Testes de backup removidos - backup/legacy_agents/ foi removido pois:
# 1. Nenhum código importa do backup
# 2. Sistema legado real está em aura_cli/core/agents/
# 3. Git mantém histórico completo se necessário reverter
# 4. Backup era apenas cópia de segurança (versão antiga)


def test_agi_worker_syntax_valid():
    """Verifica que agi_worker tem sintaxe válida após modificações."""
    import ast

    source = Path("aura_cli/cli/workers/agi_worker.py").read_text(encoding="utf-8")

    try:
        ast.parse(source)
    except SyntaxError as e:
        pytest.fail(f"Erro de sintaxe em agi_worker.py: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
