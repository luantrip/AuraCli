"""
Testes Unitários para Sistema de Extensões do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes do sistema de extensões (plugins), incluindo carregamento
dinâmico, sistema de hooks e registro de extensões.

Componentes Testados:
    - ExtensionLoader: Carregador dinâmico de extensões
    - ExtensionMetadata: Metadados de extensões
    - HookManager: Gerenciador de hooks (callbacks)
    - ExtensionRegistry: Registro centralizado de extensões
    - ExtensionStatus: Status de extensões (LOADED, ENABLED, DISABLED, etc.)

Cenários de Teste:
    - Inicialização: Criação de loader, manager e registry
    - Carregamento de Metadados: Leitura de metadata.json
    - Registro de Hooks: Registro de callbacks para eventos
    - Execução de Hooks: Execução de hooks em ordem de prioridade
    - Registro de Extensões: Registro no registry centralizado
    - Mudança de Status: Alteração de status de extensões

Validações:
    - Loader inicializa corretamente
    - Metadados são carregados
    - Hooks são registrados e executados
    - Extensões são registradas
    - Status pode ser alterado

Estrutura de Testes:
    - TestExtensionLoader: Testes do carregador
    - TestHookManager: Testes do gerenciador de hooks
    - TestExtensionRegistry: Testes do registry

Tipos de Hooks:
    - BEFORE_TOOL_CALL: Antes de chamar ferramenta
    - AFTER_TOOL_CALL: Após chamar ferramenta
    - ON_ERROR: Quando ocorre erro
    - ON_STARTUP: Na inicialização
    - ON_SHUTDOWN: No encerramento

Status de Extensões:
    - LOADED: Extensão carregada
    - ENABLED: Extensão habilitada
    - DISABLED: Extensão desabilitada
    - ERROR: Extensão com erro

ExtensionMetadata:
    Metadados de extensão:
    - name: Nome da extensão
    - version: Versão
    - description: Descrição
    - author: Autor
    - dependencies: Dependências

Exemplo de Uso:
    ```python
    def test_extensions():
        loader = ExtensionLoader("extensions")
        metadata = loader._load_metadata(extension_file)

        manager = HookManager()
        hook_id = manager.register_hook(HookType.BEFORE_TOOL_CALL, callback)
    ```

Dependências:
    - pytest: Framework de testes
    - extension_loader: Sistema de carregamento
    - hooks: Sistema de hooks
    - registry: Sistema de registro
"""

from aura_cli.core.extensions.extension_loader import ExtensionLoader
from aura_cli.core.extensions.registry import ExtensionRegistry, ExtensionStatus
from aura_cli.core.hooks.extension_hooks import HookManager, HookType


class TestExtensionLoader:
    """Testes para ExtensionLoader."""

    def test_loader_initialization(self):
        """Testa inicialização do carregador."""
        loader = ExtensionLoader(extensions_dir="extensions")

        assert loader.extensions_dir.exists()
        assert len(loader.extensions) == 0

    def test_load_metadata(self, temp_dir):
        """Testa carregamento de metadados."""
        import json

        loader = ExtensionLoader(extensions_dir=str(temp_dir))

        # Cria metadata.json
        metadata_file = temp_dir / "metadata.json"
        metadata_file.write_text(
            json.dumps(
                {
                    "name": "test_extension",
                    "version": "1.0.0",
                    "description": "Test",
                    "author": "Test Author",
                }
            )
        )

        # Cria arquivo Python
        py_file = temp_dir / "test_extension.py"
        py_file.write_text("# Test extension")

        metadata = loader._load_metadata(py_file)

        assert metadata is not None
        assert metadata.name == "test_extension"
        assert metadata.version == "1.0.0"


class TestHookManager:
    """Testes para HookManager."""

    def test_hook_manager_initialization(self):
        """Testa inicialização do gerenciador."""
        manager = HookManager()

        assert len(manager.hooks) > 0
        assert HookType.BEFORE_TOOL_CALL in manager.hooks

    def test_register_hook(self):
        """Testa registro de hook."""
        manager = HookManager()

        def callback(context):
            return "result"

        hook_id = manager.register_hook(
            HookType.BEFORE_TOOL_CALL, callback, priority=10
        )

        assert hook_id is not None
        assert len(manager.hooks[HookType.BEFORE_TOOL_CALL]) > 0

    def test_execute_hooks(self):
        """Testa execução de hooks."""
        manager = HookManager()

        results = []

        def callback(context):
            results.append(context)
            return "ok"

        manager.register_hook(HookType.BEFORE_TOOL_CALL, callback)

        manager.execute_hooks(HookType.BEFORE_TOOL_CALL, {"test": "data"})

        assert len(results) == 1
        assert results[0]["test"] == "data"


class TestExtensionRegistry:
    """Testes para ExtensionRegistry."""

    def test_registry_initialization(self):
        """Testa inicialização do registry."""
        registry = ExtensionRegistry()

        assert len(registry.extensions) == 0

    def test_register_extension(self):
        """Testa registro de extensão."""
        registry = ExtensionRegistry()

        info = registry.register("test_ext", "1.0.0", metadata={"author": "Test"})

        assert info.name == "test_ext"
        assert info.status == ExtensionStatus.LOADED
        assert "test_ext" in registry.extensions

    def test_set_status(self):
        """Testa mudança de status."""
        registry = ExtensionRegistry()
        registry.register("test_ext", "1.0.0")

        success = registry.set_status("test_ext", ExtensionStatus.ENABLED)

        assert success
        assert registry.extensions["test_ext"].status == ExtensionStatus.ENABLED
