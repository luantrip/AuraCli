"""
Testes de Integração End-to-End do Aura CLI.

Este módulo contém testes de integração que verificam fluxos completos e
interações entre múltiplos componentes do sistema. Testa cenários reais de uso
onde diferentes módulos trabalham juntos para realizar tarefas complexas.

Componentes Testados:
    - Operações de Arquivo: Ciclo completo de leitura/escrita/edição
    - Análise de Código: Integração entre criação e análise de arquivos
    - Sistema de Cache: Funcionalidade de cache e limpeza
    - Operações de Diretório: Criação e listagem de estruturas
    - Tratamento de Erros: Comportamento em casos de erro

Cenários de Teste:
    - Ciclo de Arquivo: write_file → read_file → edit_file
    - Análise de Código: write_file → analyze_code → validate_syntax
    - Cache: Uso de cache e limpeza
    - Estrutura de Diretórios: Criação → list_directory
    - Tratamento de Erros: Arquivos inexistentes, permissões, etc.

Validações:
    - Operações de arquivo funcionam em conjunto
    - Análise de código processa arquivos criados dinamicamente
    - Cache funciona corretamente
    - Estruturas de diretórios são listadas corretamente
    - Erros são tratados adequadamente

Estrutura de Testes:
    - TestFileOperationsIntegration: Testes de operações de arquivo
    - TestCodeAnalysisIntegration: Testes de análise de código
    - TestCacheIntegration: Testes de sistema de cache
    - TestDirectoryOperationsIntegration: Testes de operações de diretório
    - TestErrorHandlingIntegration: Testes de tratamento de erros

Fixtures:
    - temp_directory: Cria diretório temporário limpo para cada teste

Fluxos Testados:
    1. Criação → Leitura → Edição → Validação
    2. Escrita → Análise → Validação de Sintaxe
    3. Cache → Estatísticas → Limpeza
    4. Estrutura → Listagem → Verificação

Exemplo de Uso:
    ```python
    def test_workflow(temp_directory):
        test_file = os.path.join(temp_directory, "test.txt")
        write_file(test_file, "content")
        content = read_file(test_file)
        assert "content" in content
    ```

Dependências:
    - pytest: Framework de testes
    - tempfile: Para criação de diretórios temporários
    - shutil: Para limpeza de diretórios
    - Módulos do Aura CLI: file_system, dev_tools, ops_tools, cache
"""

import os
import shutil
import tempfile
from unittest.mock import MagicMock

import pytest

from aura_cli.core.cache import clear_cache, get_cache_stats
from aura_cli.core.logger import get_logger
from aura_cli.core.tools.dev_tools import analyze_code, edit_file, validate_syntax
from aura_cli.core.tools.file_system import list_directory, read_file, write_file

logger = get_logger(__name__)


@pytest.fixture
def temp_directory():
    """
    Fixture que cria diretório temporário para testes.

    Limpa automaticamente após cada teste.
    """
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def mock_ui_components(monkeypatch):
    """
    Fixture que mocka componentes de UI para evitar interações reais.

    Mocka:
    - console.print
    - ask_confirmation (sempre retorna True)
    - display_tool_call
    - show_tool_loading
    - display_file_edit
    - rprint
    """
    # Mock console.print
    mock_console = MagicMock()
    mock_console.print = MagicMock()

    # Mock ask_confirmation para sempre confirmar
    def mock_ask_confirmation(message, default=True, context=None, timeout=None):
        return True

    # Mock display_tool_call
    def mock_display_tool_call(tool_name, args):
        pass

    # Mock show_tool_loading
    mock_loading = MagicMock()
    mock_loading.update = MagicMock()
    mock_loading.complete = MagicMock()
    mock_loading.error = MagicMock()

    def mock_show_tool_loading(console, tool_name, args):
        return mock_loading

    # Mock display_file_edit
    def mock_display_file_edit(path, old_content, new_content, show_preview=True):
        pass

    # Mock rprint (rich.print)
    def mock_rprint(*args, **kwargs):
        pass

    # Aplicar patches usando monkeypatch.setattr nos locais corretos
    monkeypatch.setattr(
        "aura_cli.cli.ui.components.confirmation.ask_confirmation",
        mock_ask_confirmation,
    )
    monkeypatch.setattr("aura_cli.core.ui.display_tool_call", mock_display_tool_call)
    monkeypatch.setattr(
        "aura_cli.cli.ui.loading_states.show_tool_loading", mock_show_tool_loading
    )
    monkeypatch.setattr(
        "aura_cli.cli.ui.display.display_file_edit", mock_display_file_edit
    )

    # Mock rprint (rich.print) - usado em dev_tools
    try:
        import rich

        monkeypatch.setattr(rich, "print", mock_rprint)
    except Exception:
        pass

    # Mock Confirm.ask (rich.prompt.Confirm) - usado em edit_file
    def mock_confirm_ask(message, default=True):
        return True  # Sempre confirma

    try:
        from rich.prompt import Confirm

        monkeypatch.setattr(Confirm, "ask", mock_confirm_ask)
    except Exception:
        pass

    # Mock stats para evitar dependências
    mock_stats = MagicMock()
    mock_stats.skip_confirmations = True
    mock_stats.track_tool_usage = MagicMock()
    mock_stats.increment_files_created = MagicMock()
    mock_stats.increment_files_edited = MagicMock()
    mock_stats.add_shell_command = MagicMock()

    monkeypatch.setattr("aura_cli.core.stats.get_stats", lambda: mock_stats)

    return {"console": mock_console, "loading": mock_loading, "stats": mock_stats}


class TestFileOperationsIntegration:
    """Testes de integração para operações de arquivo"""

    def test_read_write_cycle_complete(self, temp_directory, mock_ui_components):
        """
        Testa ciclo completo de leitura e escrita.

        Verifica integração entre write_file e read_file.
        """
        test_file = os.path.join(temp_directory, "test.txt")
        content = "Hello, Aura CLI!"

        # Escreve (UI já está mockada)
        result = write_file(test_file, content)
        assert (
            "sucesso" in result.lower()
            or "escrito" in result.lower()
            or "criado" in result.lower()
        )

        # Lê
        read_content = read_file(test_file)
        assert content in read_content

    def test_edit_file_workflow_complete(self, temp_directory, mock_ui_components):
        """
        Testa workflow completo de edição de arquivo.

        Verifica integração entre write_file, edit_file e read_file.
        """
        test_file = os.path.join(temp_directory, "test.py")
        original = "def hello():\n    pass\n"

        # Cria arquivo (UI já está mockada)
        write_file(test_file, original)

        # Edita
        result = edit_file(test_file, "    pass", "    return 'world'")
        assert "sucesso" in result.lower() or "editado" in result.lower()

        content = read_file(test_file)
        assert "return 'world'" in content


class TestCodeAnalysisIntegration:
    """Testes de integração para análise de código"""

    def test_analyze_python_file_structure(self, temp_directory, mock_ui_components):
        """
        Testa análise de arquivo Python completo.

        Verifica integração entre write_file e analyze_code.
        """
        test_file = os.path.join(temp_directory, "test.py")
        code = """
def hello(name: str) -> str:
    return f"Hello, {name}!"

class Test:
    def method(self):
        pass
"""
        write_file(test_file, code)

        result = analyze_code(test_file)

        # analyze_code pode retornar análise estruturada
        assert isinstance(result, str)
        assert len(result) > 0
        # Pode conter informações sobre código analisado
        assert (
            "função" in result.lower()
            or "function" in result.lower()
            or "classe" in result.lower()
            or "class" in result.lower()
            or "hello" in result.lower()
        )

    def test_validate_syntax_valid_code(self):
        """
        Testa validação de sintaxe com código válido.

        Verifica se validate_syntax aceita código Python correto.
        """
        valid_python = "def test():\n    pass\n"
        result = validate_syntax(valid_python, "python")

        assert "válido" in result.lower() or "valid" in result.lower() or result == "OK"

    def test_validate_syntax_invalid_code(self):
        """
        Testa validação de sintaxe com código inválido.

        Verifica se validate_syntax detecta erros de sintaxe.
        """
        invalid_python = "def test(\n    pass\n"  # Sintaxe inválida
        result = validate_syntax(invalid_python, "python")

        assert (
            "erro" in result.lower()
            or "error" in result.lower()
            or "inválido" in result.lower()
        )


class TestCacheIntegration:
    """Testes de integração para sistema de cache"""

    def test_cache_functionality_basic(self):
        """
        Testa funcionalidade básica de cache.

        Verifica se cache funciona corretamente.
        """
        clear_cache()

        # Primeira chamada (não cacheada)
        stats1 = get_cache_stats()
        assert stats1["total_items"] == 0

        # Simula uso de função cacheada
        stats2 = get_cache_stats()
        assert isinstance(stats2, dict)
        assert "total_items" in stats2

    def test_cache_clear_functionality(self):
        """
        Testa limpeza de cache.

        Verifica se clear_cache limpa cache corretamente.
        """
        cleared = clear_cache()
        assert isinstance(cleared, int)
        assert cleared >= 0


class TestDirectoryOperationsIntegration:
    """Testes de integração para operações de diretório"""

    def test_list_directory_structure_complete(
        self, temp_directory, mock_ui_components
    ):
        """
        Testa listagem de estrutura de diretório completa.

        Verifica integração entre criação de estrutura e list_directory.
        """

        # Cria estrutura
        os.makedirs(os.path.join(temp_directory, "subdir"))
        test_file = os.path.join(temp_directory, "file.txt")
        write_file(test_file, "test")

        # Lista
        result = list_directory(temp_directory)
        # list_directory retorna tabela formatada
        assert isinstance(result, str)
        assert len(result) > 0
        # Pode conter os itens ou mensagem de sucesso
        assert (
            "file.txt" in result
            or "subdir" in result
            or "sucesso" in result.lower()
            or "listou" in result.lower()
        )


class TestErrorHandlingIntegration:
    """Testes de integração para tratamento de erros"""

    def test_read_nonexistent_file_handles_error(self):
        """
        Testa leitura de arquivo inexistente.

        Verifica tratamento de erro quando arquivo não existe.
        """
        result = read_file("/nonexistent/file.txt")

        assert (
            "erro" in result.lower()
            or "não encontrado" in result.lower()
            or "not found" in result.lower()
        )

    def test_edit_nonexistent_file_handles_error(
        self, temp_directory, mock_ui_components
    ):
        """
        Testa edição de arquivo inexistente.

        Verifica tratamento de erro quando tenta editar arquivo que não existe.
        """
        test_file = os.path.join(temp_directory, "nonexistent.txt")

        result = edit_file(test_file, "old", "new")

        assert (
            "erro" in result.lower()
            or "não encontrado" in result.lower()
            or "not found" in result.lower()
        )
