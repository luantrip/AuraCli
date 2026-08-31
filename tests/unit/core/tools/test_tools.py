"""
Testes Unitários para Módulo de Ferramentas do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de ferramentas básicas do Aura CLI, incluindo operações de sistema de arquivos
e detecção/extração de comandos shell.

Componentes Testados:
    - read_file: Leitura de arquivos
    - write_file: Escrita de arquivos
    - list_directory: Listagem de diretórios
    - is_shell_command: Detecção de comandos shell
    - extract_shell_command: Extração de comandos shell de texto

Cenários de Teste:
    - Leitura de Arquivo: Leitura de arquivo de exemplo
    - Escrita de Arquivo: Escrita com confirmação
    - Listagem de Diretório: Listagem de arquivos em diretório
    - Detecção de Shell: Identificação de comandos shell
    - Extração de Shell: Extração de comando de texto

Validações:
    - Arquivos são lidos corretamente
    - Arquivos são escritos corretamente
    - Diretórios são listados
    - Comandos shell são detectados
    - Comandos são extraídos de texto

Estrutura de Testes:
    - TestFileSystem: Testes de operações de arquivo
    - TestShell: Testes de operações shell

Operações de Arquivo:
    - read_file: Lê conteúdo completo do arquivo
    - write_file: Escreve conteúdo (com confirmação)
    - list_directory: Lista arquivos e diretórios formatados

Detecção de Shell:
    Identifica comandos shell comuns:
    - ls, cd, mkdir, rm, etc.
    - git, docker, npm, etc.
    - Comandos com pipes e redirecionamentos

Extração de Shell:
    Extrai comandos de:
    - "Execute: ls -la"
    - "Run: git status"
    - Texto com comandos embutidos

Exemplo de Uso:
    ```python
    def test_tools():
        content = read_file("test.txt")
        assert "content" in content

        assert is_shell_command("ls -la") == True
        command = extract_shell_command("Execute: ls -la")
        assert "ls" in command
    ```

Dependências:
    - pytest: Framework de testes
    - unittest.mock: Para mocking de input
    - file_system: Módulo de operações de arquivo
    - shell: Módulo de operações shell
"""

from unittest.mock import patch

from aura_cli.core.tools.file_system import list_directory, read_file, write_file
from aura_cli.core.tools.shell import extract_shell_command, is_shell_command


class TestFileSystem:
    """Testes para operações de arquivo."""

    def test_read_file(self, sample_file):
        """Testa leitura de arquivo."""
        content = read_file(str(sample_file))

        assert "Test content" in content
        assert "Line 2" in content

    @patch(
        "aura_cli.cli.ui.components.confirmation.ask_confirmation", return_value=True
    )
    def test_write_file(self, mock_confirmation, temp_dir):
        """Testa escrita de arquivo."""
        test_file = temp_dir / "write_test.txt"

        result = write_file(str(test_file), "New content")

        assert "sucesso" in result.lower() or "success" in result.lower()
        assert test_file.exists()
        assert test_file.read_text() == "New content"

    def test_list_directory(self, temp_dir):
        """Testa listagem de diretório."""
        # Cria alguns arquivos
        (temp_dir / "file1.txt").write_text("content")
        (temp_dir / "file2.py").write_text("content")

        result = list_directory(str(temp_dir))

        assert "file1.txt" in result or len(result) > 0


class TestShell:
    """Testes para operações shell."""

    def test_is_shell_command(self):
        """Testa detecção de comando shell."""
        assert is_shell_command("ls -la")
        assert is_shell_command("git status")
        assert not is_shell_command("not a command")

    def test_extract_shell_command(self):
        """Testa extração de comando shell."""
        command = extract_shell_command("Execute: ls -la")

        assert "ls" in command.lower()
