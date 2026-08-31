"""
Testes para Ferramentas de Desenvolvimento do Aura CLI.

Este módulo contém testes abrangentes para todas as ferramentas de desenvolvimento
do Aura CLI, incluindo edição de arquivos, busca em código, visualização de árvore,
análise de código, validação de sintaxe e sistema de backup/restore.

Componentes Testados:
    - edit_file: Edição segura de arquivos com substituição de conteúdo
    - find_in_files: Busca de padrões em múltiplos arquivos
    - tree_view: Visualização de estrutura de diretórios
    - analyze_code: Análise estática de código (Python, JavaScript, etc.)
    - backup_file: Criação de backups automáticos
    - restore_backup: Restauração de backups
    - validate_syntax: Validação de sintaxe para múltiplas linguagens

Cenários de Teste:
    - Edição de Arquivos: Substituição bem-sucedida, conteúdo não encontrado, arquivo inexistente
    - Busca em Arquivos: Busca básica, sem resultados, busca com regex
    - Visualização de Árvore: Estrutura básica, ignorar diretórios comuns, limite de profundidade
    - Análise de Código: Python (classes, funções, imports), JavaScript (componentes, funções)
    - Backup/Restore: Criação de backup, restauração de conteúdo
    - Validação: Código válido/inválido (Python, JSON)

Validações:
    - Edições são aplicadas corretamente
    - Buscas encontram padrões esperados
    - Árvore mostra estrutura correta
    - Análise identifica elementos de código
    - Backups são criados e restaurados corretamente
    - Validação detecta erros de sintaxe

Estrutura de Testes:
    - TestEditFile: Testes de edição de arquivos
    - TestFindInFiles: Testes de busca em arquivos
    - TestTreeView: Testes de visualização de árvore
    - TestAnalyzeCode: Testes de análise de código
    - TestBackupRestore: Testes de backup e restore
    - TestValidateSyntax: Testes de validação de sintaxe

Suporte a Linguagens:
    - Python: Análise completa de AST
    - JavaScript: Análise de estruturas ES6+
    - JSON: Validação de sintaxe
    - (Extensível para outras linguagens)

Exemplo de Uso:
    ```python
    def test_edit():
        result = edit_file("test.txt", "old", "new")
        assert "sucesso" in result.lower()
    ```

Dependências:
    - pytest: Framework de testes
    - unittest.mock: Para mocking de input
    - pathlib: Para manipulação de caminhos
"""

import os
from pathlib import Path

from aura_cli.core.tools.dev_tools import (
    analyze_code,
    backup_file,
    edit_file,
    find_in_files,
    restore_backup,
    tree_view,
    validate_syntax,
)


class TestEditFile:
    """Testes para função edit_file"""

    def test_edit_file_successful_replacement(self, tmp_path, monkeypatch):
        """
        Testa edição bem-sucedida de arquivo.

        Verifica se edit_file substitui conteúdo corretamente.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World\nThis is a test", encoding="utf-8")

        def mock_ask_confirmation(*args, **kwargs):
            return True

        def mock_confirm_ask(*args, **kwargs):
            return True

        monkeypatch.setattr(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            mock_ask_confirmation,
        )
        try:
            from rich.prompt import Confirm

            monkeypatch.setattr(Confirm, "ask", mock_confirm_ask)
        except Exception:
            pass

        result = edit_file(str(test_file), "World", "Python")

        assert "sucesso" in result.lower() or "editado" in result.lower()
        assert "Hello Python" in test_file.read_text(encoding="utf-8")

    def test_edit_file_content_not_found(self, tmp_path, monkeypatch):
        """
        Testa edição quando conteúdo antigo não é encontrado.

        Verifica tratamento quando old_content não existe no arquivo.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello World", encoding="utf-8")

        def mock_ask_confirmation(*args, **kwargs):
            return True

        def mock_confirm_ask(*args, **kwargs):
            return True

        monkeypatch.setattr(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            mock_ask_confirmation,
        )
        try:
            from rich.prompt import Confirm

            monkeypatch.setattr(Confirm, "ask", mock_confirm_ask)
        except Exception:
            pass

        result = edit_file(str(test_file), "NotFound", "Something")

        assert "não encontrado" in result.lower() or "not found" in result.lower()

    def test_edit_file_nonexistent_file(self, tmp_path, monkeypatch):
        """
        Testa edição de arquivo inexistente.

        Verifica tratamento de erro quando arquivo não existe.
        """
        test_file = tmp_path / "nonexistent.txt"

        def mock_ask_confirmation(*args, **kwargs):
            return True

        def mock_confirm_ask(*args, **kwargs):
            return True

        monkeypatch.setattr(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            mock_ask_confirmation,
        )
        try:
            from rich.prompt import Confirm

            monkeypatch.setattr(Confirm, "ask", mock_confirm_ask)
        except Exception:
            pass

        result = edit_file(str(test_file), "old", "new")

        assert "erro" in result.lower() or "não encontrado" in result.lower()


class TestFindInFiles:
    """Testes para função find_in_files"""

    def test_find_in_files_basic_search(self, tmp_path):
        """
        Testa busca básica em arquivos.

        Verifica se find_in_files encontra padrões corretamente.
        """
        (tmp_path / "file1.py").write_text(
            "def hello():\n    print('world')", encoding="utf-8"
        )
        (tmp_path / "file2.py").write_text(
            "def goodbye():\n    print('world')", encoding="utf-8"
        )
        (tmp_path / "file3.txt").write_text("world", encoding="utf-8")

        result = find_in_files("world", str(tmp_path), [".py"])

        assert "file1.py" in result
        assert "file2.py" in result
        # file3.txt não deve aparecer se filtrado por .py
        if ".py" in str(result):
            assert "file3.txt" not in result

    def test_find_in_files_no_results(self, tmp_path):
        """
        Testa busca quando não há resultados.

        Verifica comportamento quando padrão não é encontrado.
        """
        (tmp_path / "file.py").write_text("def hello(): pass", encoding="utf-8")

        result = find_in_files("notfound", str(tmp_path))

        assert (
            "nenhum resultado" in result.lower()
            or "not found" in result.lower()
            or len(result) == 0
        )

    def test_find_in_files_with_regex(self, tmp_path):
        """
        Testa busca com padrão regex.

        Verifica se find_in_files suporta padrões regex.
        """
        (tmp_path / "test.py").write_text(
            "def function1():\n    pass\ndef function2():\n    pass", encoding="utf-8"
        )

        result = find_in_files("function\\d+", str(tmp_path))

        assert "function1" in result or "function2" in result or "test.py" in result


class TestTreeView:
    """Testes para função tree_view"""

    def test_tree_view_basic_structure(self, tmp_path):
        """
        Testa geração de árvore básica.

        Verifica se tree_view mostra estrutura de diretórios corretamente.
        """
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# main", encoding="utf-8")
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_main.py").write_text("# test", encoding="utf-8")
        (tmp_path / "README.md").write_text("# README", encoding="utf-8")

        result = tree_view(str(tmp_path), max_depth=2)

        assert "src" in result
        assert "tests" in result
        assert "README.md" in result

    def test_tree_view_ignores_common_dirs(self, tmp_path):
        """
        Testa que diretórios comuns são ignorados.

        Verifica se tree_view ignora node_modules, __pycache__, etc.
        """
        (tmp_path / "node_modules").mkdir()
        (tmp_path / "__pycache__").mkdir()
        (tmp_path / "src").mkdir()

        result = tree_view(str(tmp_path))

        assert "node_modules" not in result
        assert "__pycache__" not in result
        assert "src" in result

    def test_tree_view_respects_max_depth(self, tmp_path):
        """
        Testa que max_depth é respeitado.

        Verifica se tree_view limita profundidade corretamente.
        """
        (tmp_path / "level1").mkdir()
        (tmp_path / "level1" / "level2").mkdir()
        (tmp_path / "level1" / "level2" / "level3").mkdir()

        result = tree_view(str(tmp_path), max_depth=2)

        # level3 não deve aparecer se max_depth=2
        if "level3" in result:
            # Se aparecer, deve ser truncado ou indicado
            assert "..." in result or "truncated" in result.lower()


class TestAnalyzeCode:
    """Testes para função analyze_code"""

    def test_analyze_python_file_structure(self, tmp_path):
        """
        Testa análise de arquivo Python.

        Verifica se analyze_code identifica classes, funções e imports.
        """
        test_file = tmp_path / "test.py"
        test_file.write_text(
            """
import os
from pathlib import Path

class MyClass:
    def method1(self):
        pass

    def method2(self, arg):
        return arg

def my_function(x, y):
    return x + y

def another_function():
    pass
""",
            encoding="utf-8",
        )

        result = analyze_code(str(test_file))

        assert "MyClass" in result
        assert "my_function" in result or "my_function" in result.lower()
        assert "import" in result.lower() or "os" in result

    def test_analyze_javascript_file(self, tmp_path):
        """
        Testa análise de arquivo JavaScript.

        Verifica se analyze_code identifica estruturas JavaScript.
        """
        test_file = tmp_path / "test.js"
        test_file.write_text(
            """
import React from 'react';
import { useState } from 'react';

class MyComponent {
    render() {
        return null;
    }
}

function myFunction() {
    console.log('hello');
}

const arrowFunc = () => {
    return 42;
};
""",
            encoding="utf-8",
        )

        result = analyze_code(str(test_file))

        assert "MyComponent" in result
        assert "myFunction" in result or "my_function" in result.lower()


class TestBackupRestore:
    """Testes para backup_file e restore_backup"""

    def test_backup_file_creates_backup(self, tmp_path):
        """
        Testa criação de backup.

        Verifica se backup_file cria arquivo de backup corretamente.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("original content", encoding="utf-8")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = backup_file("test.txt")

            assert "backup criado" in result.lower() or ".aura/backups" in result
            assert Path(".aura/backups").exists()
        finally:
            os.chdir(original_cwd)

    def test_restore_backup_restores_content(self, tmp_path, monkeypatch):
        """
        Testa restauração de backup.

        Verifica se restore_backup restaura conteúdo original.
        """
        test_file = tmp_path / "test.txt"
        test_file.write_text("original", encoding="utf-8")

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Cria backup
            backup_file("test.txt")

            test_file.write_text("modified", encoding="utf-8")

            # Mock input para confirmar
            def mock_ask_confirmation(*args, **kwargs):
                return True

            def mock_confirm_ask(*args, **kwargs):
                return True

            monkeypatch.setattr(
                "aura_cli.cli.ui.components.confirmation.ask_confirmation",
                mock_ask_confirmation,
            )
            try:
                from rich.prompt import Confirm

                monkeypatch.setattr(Confirm, "ask", mock_confirm_ask)
            except Exception:
                pass

            # Restaura
            result = restore_backup("test.txt")

            assert "restaurado" in result.lower() or "restored" in result.lower()
            assert test_file.read_text(encoding="utf-8") == "original"
        finally:
            os.chdir(original_cwd)


class TestValidateSyntax:
    """Testes para função validate_syntax"""

    def test_validate_python_valid_code(self):
        """
        Testa validação de código Python válido.

        Verifica se validate_syntax aceita código Python correto.
        """
        code = "def hello():\n    return 'world'"

        result = validate_syntax(code, "python")

        assert result == "OK" or "válido" in result.lower() or "valid" in result.lower()

    def test_validate_python_invalid_code(self):
        """
        Testa validação de código Python inválido.

        Verifica se validate_syntax detecta erros de sintaxe.
        """
        code = "def hello(\n    return 'world'"  # Sintaxe inválida

        result = validate_syntax(code, "python")

        assert (
            "erro" in result.lower()
            or "error" in result.lower()
            or "inválido" in result.lower()
        )

    def test_validate_json_valid(self):
        """
        Testa validação de JSON válido.

        Verifica se validate_syntax aceita JSON correto.
        """
        code = '{"name": "test", "value": 42}'

        result = validate_syntax(code, "json")

        assert result == "OK" or "válido" in result.lower()

    def test_validate_json_invalid(self):
        """
        Testa validação de JSON inválido.

        Verifica se validate_syntax detecta erros em JSON.
        """
        code = '{"name": "test", value: 42}'  # Sem aspas na chave

        result = validate_syntax(code, "json")

        assert "erro" in result.lower() or "error" in result.lower()
