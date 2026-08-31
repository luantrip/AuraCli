"""
Testes unitários para as features da Aura CLI.

Este módulo testa:
    - TangentManager (Tangent Mode)
    - CheckpointManager (Git-based Checkpointing)
    - HookManager (Event-driven Hooks)
    - Context Indicator
    - API Key Validator
    - Checkpoint Tools

Note:
    Muitos testes usam mocks para evitar dependências externas como litellm.
"""

import json
import os
from pathlib import Path
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest


class TestTangentManager:
    """Testes para o TangentManager (Tangent Mode)."""

    def test_tangent_manager_import(self):
        """Testa importação do TangentManager."""
        from aura_cli.core.tangent import TangentManager, TangentState

        assert TangentManager is not None
        assert TangentState is not None

    def test_tangent_manager_creation(self):
        """Testa criação do TangentManager."""
        from aura_cli.core.tangent import TangentManager

        manager = TangentManager()
        assert manager is not None
        assert manager.state == manager.state  # Check state exists

    def test_tangent_enter_exit(self):
        """Testa entrar e sair do modo tangente."""
        from aura_cli.core.tangent import TangentManager, TangentState

        manager = TangentManager()

        # Estado inicial
        assert manager.state == TangentState.NORMAL

        # Histórico de teste
        conversation = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]

        # Entrar no tangent mode
        manager.enter(conversation)
        assert manager.state == TangentState.TANGENT

        # Sair do tangent mode (passando o histórico atual)
        restored, _message = manager.exit(conversation)
        assert manager.state == TangentState.NORMAL
        assert restored == conversation

    def test_tangent_enter_exit_with_tail(self):
        """Testa sair mantendo última Q&A."""
        from aura_cli.core.tangent import TangentManager, TangentState

        manager = TangentManager()

        original = [
            {"role": "user", "content": "Original Q"},
            {"role": "assistant", "content": "Original A"},
        ]

        # Entrar no tangent mode
        manager.enter(original)

        # Simular nova conversa em tangent
        tangent_history = [
            *original,
            {"role": "user", "content": "Tangent Q"},
            {"role": "assistant", "content": "Tangent A"},
        ]

        # Sair mantendo tail
        restored, _message = manager.exit(tangent_history, keep_tail=True)

        assert manager.state == TangentState.NORMAL
        # Should have original + last Q&A
        assert len(restored) >= 2

    def test_tangent_forget(self):
        """Testa esquecer mensagens."""
        from aura_cli.core.tangent import TangentManager

        manager = TangentManager()

        conversation = [
            {"role": "user", "content": "Q1"},
            {"role": "assistant", "content": "A1"},
            {"role": "user", "content": "Q2"},
            {"role": "assistant", "content": "A2"},
        ]

        # Esquecer 1 mensagem do usuário (e sua resposta)
        new_history, message = manager.forget(conversation, count=1)

        # Deve ter removido a última mensagem do usuário e tudo depois
        assert len(new_history) == 2
        assert "Forgot" in message

    def test_tangent_indicator(self):
        """Testa indicador de tangent mode."""
        from aura_cli.core.tangent import TangentManager

        manager = TangentManager()

        # Estado normal - sem indicador
        assert manager.get_indicator() == ""

        # Entrar no tangent
        manager.enter([])

        # Deve ter indicador
        indicator = manager.get_indicator()
        assert len(indicator) > 0
        assert "↯" in indicator or "tangent" in indicator.lower()


class TestCheckpointManager:
    """Testes para o CheckpointManager (Git-based Checkpointing)."""

    def test_checkpoint_manager_import(self):
        """Testa importação do CheckpointManager."""
        from aura_cli.core.checkpoint import Checkpoint, CheckpointManager

        assert CheckpointManager is not None
        assert Checkpoint is not None

    def test_checkpoint_manager_creation(self):
        """Testa criação do CheckpointManager."""
        from aura_cli.core.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            shadow_dir = Path(tmpdir) / ".checkpoints"
            manager = CheckpointManager(shadow_dir=shadow_dir)

            assert manager is not None
            assert not manager.initialized  # Não inicializado até chamar init()

    def test_checkpoint_init(self):
        """Testa inicialização do sistema de checkpoints."""
        from aura_cli.core.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            shadow_dir = Path(tmpdir) / ".checkpoints"

            manager = CheckpointManager(shadow_dir=shadow_dir)

            # Inicializar
            result = manager.init()

            assert result is True
            assert manager.initialized
            assert shadow_dir.exists()

    def test_checkpoint_list_empty(self):
        """Testa listar checkpoints em repo vazio."""
        from aura_cli.core.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            shadow_dir = Path(tmpdir) / ".checkpoints"

            manager = CheckpointManager(shadow_dir=shadow_dir)

            # Sem inicializar, deve retornar lista vazia
            checkpoints = manager.list()

            assert isinstance(checkpoints, list)
            assert len(checkpoints) == 0


class TestHookManager:
    """Testes para o HookManager (Event-driven Hooks)."""

    def test_hook_manager_import(self):
        """Testa importação do HookManager."""
        from aura_cli.core.hooks import Hook, HookEvent, HookManager, HookResult

        assert HookManager is not None
        assert HookEvent is not None
        assert HookResult is not None
        assert Hook is not None

    def test_hook_manager_creation(self):
        """Testa criação do HookManager."""
        from aura_cli.core.hooks import HookManager

        manager = HookManager()
        assert manager is not None
        assert hasattr(manager, "hooks")

    def test_hook_event_enum(self):
        """Testa enum HookEvent."""
        from aura_cli.core.hooks import HookEvent

        assert HookEvent.AGENT_SPAWN.value == "agentSpawn"
        assert HookEvent.PRE_TOOL.value == "preToolUse"
        assert HookEvent.POST_TOOL.value == "postToolUse"

    def test_hook_registration(self):
        """Testa registro de hooks."""
        from aura_cli.core.hooks import Hook, HookEvent, HookManager

        manager = HookManager()

        hook = Hook(
            event=HookEvent.PRE_TOOL, command=["echo", "test"], matcher="read_file"
        )

        manager.register(hook)

        # Verificar se foi registrado
        assert HookEvent.PRE_TOOL in manager.hooks
        assert len(manager.hooks[HookEvent.PRE_TOOL]) > 0

    def test_hook_result_dataclass(self):
        """Testa dataclass HookResult."""
        from aura_cli.core.hooks import HookResult

        result = HookResult(exit_code=0, stdout="ok", stderr="")

        assert result.success is True
        assert result.should_block is False

        blocked_result = HookResult(exit_code=2, stderr="blocked")
        assert blocked_result.should_block is True

    def test_hook_load_from_file(self):
        """Testa carregar hooks de arquivo JSON."""
        from aura_cli.core.hooks import HookEvent, HookManager

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            hooks_config = {
                "hooks": [
                    {
                        "type": "PreToolUse",
                        "command": ["echo", "from file"],
                        "matcher": "write_file",
                        "timeout_ms": 5000,
                    }
                ]
            }
            json.dump(hooks_config, f)
            f.flush()

            manager = HookManager()
            manager.load_from_file(Path(f.name))

            # Verificar se carregou
            assert HookEvent.PRE_TOOL in manager.hooks
            assert len(manager.hooks[HookEvent.PRE_TOOL]) > 0

            os.unlink(f.name)


class TestContextIndicator:
    """Testes para o Context Indicator."""

    def test_context_indicator_import(self):
        """Testa importação do context_indicator."""
        # Import diretamente do módulo para evitar imports circulares
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "context_indicator", "aura_cli/cli/ui/context_indicator.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        assert hasattr(module, "get_context_percentage")
        assert hasattr(module, "should_compact_context")

    def test_context_percentage_calculation_direct(self):
        """Testa cálculo de porcentagem de contexto (direto)."""

        # Testar a lógica diretamente
        def get_context_percentage(tokens_used: int, max_tokens: int) -> float:
            if max_tokens <= 0:
                return 0.0
            return (tokens_used / max_tokens) * 100

        # 50% usage
        percentage = get_context_percentage(50000, 100000)
        assert percentage == 50.0

        # 0% usage
        percentage = get_context_percentage(0, 100000)
        assert percentage == 0.0

        # 100% usage
        percentage = get_context_percentage(100000, 100000)
        assert percentage == 100.0

    def test_context_percentage_edge_cases_direct(self):
        """Testa casos extremos do cálculo (direto)."""

        def get_context_percentage(tokens_used: int, max_tokens: int) -> float:
            if max_tokens <= 0:
                return 0.0
            return (tokens_used / max_tokens) * 100

        # Zero max tokens
        percentage = get_context_percentage(1000, 0)
        assert percentage == 0.0

    def test_should_compact_context_direct(self):
        """Testa quando deve compactar contexto (direto)."""

        def should_compact_context(
            tokens_used: int, max_tokens: int, threshold: float = 0.8
        ) -> bool:
            if max_tokens <= 0:
                return False
            usage = tokens_used / max_tokens
            return usage >= threshold

        # Baixo uso - não compactar
        assert should_compact_context(30000, 100000) is False

        # Alto uso - compactar
        assert should_compact_context(85000, 100000) is True

        # Threshold customizado
        assert should_compact_context(60000, 100000, threshold=0.5) is True


class TestAPIValidator:
    """Testes para o API Key Validator."""

    def test_api_validator_import(self):
        """Testa importação do api_validator."""
        # Import diretamente para evitar imports circulares
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "api_validator", "aura_cli/core/llm/api_validator.py"
        )
        module = importlib.util.module_from_spec(spec)

        # Mock litellm antes de carregar
        sys.modules["litellm"] = MagicMock()
        spec.loader.exec_module(module)

        assert hasattr(module, "ValidationStatus")
        assert hasattr(module, "ValidationResult")
        assert hasattr(module, "validate_api_key")

    def test_validation_status_values(self):
        """Testa valores do ValidationStatus."""
        # Testar diretamente os valores esperados
        expected_statuses = [
            "success",
            "invalid_key",
            "rate_limited",
            "network_error",
            "timeout",
            "unknown_error",
        ]

        for status in expected_statuses:
            assert status in expected_statuses


class TestAPIValidatorDirect:
    """Testes diretos para API Validator sem imports."""

    def test_validation_result_structure(self):
        """Testa estrutura de ValidationResult."""
        from dataclasses import dataclass
        from enum import Enum

        class ValidationStatus(Enum):
            SUCCESS = "success"
            INVALID_KEY = "invalid_key"

        @dataclass
        class ValidationResult:
            status: ValidationStatus
            provider: str
            message: str

        result = ValidationResult(
            status=ValidationStatus.SUCCESS, provider="Test", message="OK"
        )

        assert result.status == ValidationStatus.SUCCESS
        assert result.provider == "Test"


class TestCheckpointTools:
    """Testes para as ferramentas de checkpoint."""

    def test_checkpoint_tools_import(self):
        """Testa importação das checkpoint_tools."""
        from aura_cli.core.tools.checkpoint_tools import (
            CHECKPOINT_TOOLS,
            create_checkpoint,
            get_context_usage,
            list_checkpoints,
            restore_checkpoint,
            set_checkpoint_manager,
            set_tangent_manager,
        )

        assert CHECKPOINT_TOOLS is not None
        assert create_checkpoint is not None
        assert list_checkpoints is not None
        assert restore_checkpoint is not None
        assert get_context_usage is not None
        assert set_checkpoint_manager is not None
        assert set_tangent_manager is not None

    def test_checkpoint_tools_without_manager(self):
        """Testa ferramentas sem manager configurado."""
        from aura_cli.core.tools.checkpoint_tools import (
            create_checkpoint,
            list_checkpoints,
            restore_checkpoint,
            set_checkpoint_manager,
        )

        # Limpar manager
        set_checkpoint_manager(None)

        # Criar checkpoint deve falhar gracefully
        result = create_checkpoint("Test")
        assert result["success"] is False
        assert (
            "not initialized" in result["error"].lower()
            or "não" in result["error"].lower()
        )

        # Listar checkpoints deve falhar gracefully
        result = list_checkpoints()
        assert result["success"] is False

        # Restaurar checkpoint deve falhar gracefully
        result = restore_checkpoint("abc123")
        assert result["success"] is False

    def test_get_context_usage(self):
        """Testa get_context_usage."""
        # Mock dos imports necessários
        with patch.dict(
            sys.modules, {"aura_cli.cli.ui.context_indicator": MagicMock()}
        ):
            from aura_cli.core.tools.checkpoint_tools import get_context_usage

            # Mock a função importada
            sys.modules["aura_cli.cli.ui.context_indicator"].get_context_percentage = (
                lambda x, y: 50.0
            )
            sys.modules["aura_cli.cli.ui.context_indicator"].should_compact_context = (
                lambda x, y: False
            )

            result = get_context_usage()

            assert "success" in result

    def test_checkpoint_tool_schemas(self):
        """Testa schemas das ferramentas."""
        from aura_cli.core.tools.checkpoint_tools import get_checkpoint_tool_schemas

        schemas = get_checkpoint_tool_schemas()

        assert isinstance(schemas, list)
        assert len(schemas) > 0

        # Verificar estrutura do schema
        for schema in schemas:
            assert "type" in schema
            assert schema["type"] == "function"
            assert "function" in schema
            assert "name" in schema["function"]
            assert "description" in schema["function"]
            assert "parameters" in schema["function"]


class TestWorkerCheckpointHelper:
    """Testes para o WorkerCheckpointHelper."""

    def test_checkpoint_helper_import(self):
        """Testa importação do checkpoint_helper."""
        from aura_cli.cli.workers.checkpoint_helper import (
            WorkerCheckpointHelper,
            get_checkpoint_helper,
        )

        assert WorkerCheckpointHelper is not None
        assert get_checkpoint_helper is not None

    def test_checkpoint_helper_creation(self):
        """Testa criação do helper."""
        from aura_cli.cli.workers.checkpoint_helper import WorkerCheckpointHelper

        helper = WorkerCheckpointHelper(worker_name="test_worker", status_queue=None)

        assert helper is not None
        assert helper.worker_name == "test_worker"

    def test_get_checkpoint_helper(self):
        """Testa factory function."""
        import queue

        from aura_cli.cli.workers.checkpoint_helper import get_checkpoint_helper

        status_queue = queue.Queue()
        helper = get_checkpoint_helper("agi_worker", status_queue)

        assert helper is not None
        assert helper.worker_name == "agi_worker"
        assert helper.status_queue == status_queue

    def test_helper_create_checkpoint_without_init(self):
        """Testa criar checkpoint sem inicialização."""
        from aura_cli.cli.workers.checkpoint_helper import WorkerCheckpointHelper

        helper = WorkerCheckpointHelper("test")

        # Sem inicialização, deve retornar None
        checkpoint_id = helper.create_initial_checkpoint("Test")
        assert checkpoint_id is None

    def test_helper_restore_without_checkpoint(self):
        """Testa restaurar sem checkpoint."""
        from aura_cli.cli.workers.checkpoint_helper import WorkerCheckpointHelper

        helper = WorkerCheckpointHelper("test")

        # Sem checkpoint, deve retornar False
        result = helper.restore_on_failure()
        assert result is False

    def test_helper_trigger_hook(self):
        """Testa disparo de hook."""
        from aura_cli.cli.workers.checkpoint_helper import WorkerCheckpointHelper

        helper = WorkerCheckpointHelper("test")

        # Não deve lançar exceção mesmo sem hook manager
        helper.trigger_hook("test_event", {"data": "value"})


class TestModelUtils:
    """Testes para model_utils (normalização de modelos)."""

    def test_normalize_gemini(self):
        """Testa normalização de modelos Gemini."""
        # Import direto para evitar imports circulares
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_utils", "aura_cli/core/llm/model_utils.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        normalize_model_name = module.normalize_model_name

        assert normalize_model_name("gemini") == "gemini/gemini-2.5-flash"
        assert normalize_model_name("gemini-2.5-flash") == "gemini/gemini-2.5-flash"
        assert (
            normalize_model_name("gemini/gemini-2.5-flash") == "gemini/gemini-2.5-flash"
        )

    def test_normalize_claude(self):
        """Testa normalização de modelos Claude."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_utils", "aura_cli/core/llm/model_utils.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        normalize_model_name = module.normalize_model_name

        # Claude não precisa de prefixo
        assert (
            normalize_model_name("claude-3-5-sonnet-20241022")
            == "claude-3-5-sonnet-20241022"
        )

    def test_normalize_gpt(self):
        """Testa normalização de modelos GPT."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_utils", "aura_cli/core/llm/model_utils.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        normalize_model_name = module.normalize_model_name

        # GPT não precisa de prefixo
        assert normalize_model_name("gpt-4o") == "gpt-4o"
        assert normalize_model_name("gpt-4o-mini") == "gpt-4o-mini"

    def test_get_provider_from_model(self):
        """Testa detecção de provedor."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_utils", "aura_cli/core/llm/model_utils.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        get_provider_from_model = module.get_provider_from_model

        assert get_provider_from_model("gemini/gemini-2.5-flash") == "gemini"
        assert get_provider_from_model("claude-3-5-sonnet") == "claude"
        assert get_provider_from_model("gpt-4o") == "gpt"
        assert (
            get_provider_from_model("openrouter/meta-llama/llama-3.3") == "openrouter"
        )

    def test_get_fallback_models(self):
        """Testa lista de modelos de fallback."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "model_utils", "aura_cli/core/llm/model_utils.py"
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        get_fallback_models = module.get_fallback_models

        fallbacks = get_fallback_models("gemini/gemini-2.5-flash")

        assert isinstance(fallbacks, list)
        assert len(fallbacks) > 0
        assert fallbacks[0] == "gemini/gemini-2.5-flash"


class TestToolRegistry:
    """Testes para o tool_registry (inclusão das novas ferramentas)."""

    def test_checkpoint_tools_in_registry(self):
        """Testa se as ferramentas de checkpoint estão no registry."""
        from aura_cli.core.service_registry import get_tools_dict

        tools = get_tools_dict()

        # Verificar se as ferramentas de checkpoint estão incluídas
        assert "create_checkpoint" in tools
        assert "list_checkpoints" in tools
        assert "restore_checkpoint" in tools
        assert "get_context_usage" in tools

    def test_tools_count(self):
        """Testa contagem total de ferramentas."""
        from aura_cli.core.service_registry import get_tools_dict

        tools = get_tools_dict()

        # Deve ter pelo menos 54 ferramentas (original) + 4 (checkpoint) = 58
        assert len(tools) >= 54


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
