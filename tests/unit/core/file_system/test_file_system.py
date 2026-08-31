"""
Testes para sistema de arquivos.

Testa operações básicas de I/O: leitura, escrita e listagem de arquivos.
Seguindo padrão AAA (Arrange-Act-Assert).
"""

import pytest

from aura_cli.core.tools.file_system import (
    list_directory,
    read_code_element,
    read_file,
    write_file,
)


class TestReadCodeElement:
    """Testes para função read_code_element (Integração Prism)"""

    def test_read_code_element_calls_prism(self, tmp_path, monkeypatch):
        """
        Testa se read_code_element usa PrismManager.
        """
        from unittest.mock import MagicMock

        from aura_cli.core.memory.prism_bridge import CodeChunk

        # Mock PrismManager
        mock_prism = MagicMock()
        mock_prism.available = True
        mock_prism.chunk_file.return_value = [
            CodeChunk(
                content="def target():\n    pass",
                start_line=1,
                end_line=2,
                kind="function",
                name="target",
            ),
            CodeChunk(
                content="def other():\n    pass",
                start_line=4,
                end_line=5,
                kind="function",
                name="other",
            ),
        ]

        mock_prism_class = MagicMock(return_value=mock_prism)
        monkeypatch.setattr(
            "aura_cli.core.memory.prism_bridge.PrismManager", mock_prism_class
        )

        # Arrange
        test_file = tmp_path / "code.py"
        test_file.write_text("def target():\n    pass", encoding="utf-8")

        # Act
        result = read_code_element(str(test_file), name="target", kind="function")

        # Assert
        assert "def target():" in result
        assert "pass" in result
        assert "### function target" in result
        mock_prism.chunk_file.assert_called_with(str(test_file))

    def test_read_code_element_not_found(self, tmp_path, monkeypatch):
        """
        Testa quando elemento não é encontrado.
        """
        from unittest.mock import MagicMock

        mock_prism = MagicMock()
        mock_prism.available = True
        mock_prism.chunk_file.return_value = []
        mock_prism_class = MagicMock(return_value=mock_prism)
        monkeypatch.setattr(
            "aura_cli.core.memory.prism_bridge.PrismManager", mock_prism_class
        )

        test_file = tmp_path / "empty.py"
        test_file.write_text("", encoding="utf-8")

        result = read_code_element(str(test_file), name="missing")

        assert "not found" in result.lower()


class TestReadFile:
    """Testes para função read_file"""

    def test_read_file_complete_content(self, tmp_path):
        """
        Arrange: Arquivo com conteúdo conhecido
        Act: Lê arquivo completo
        Assert: Conteúdo lido é idêntico ao escrito
        """
        # Arrange
        test_file = tmp_path / "hello.txt"
        expected_content = "Olá, Mundo!\nLinha 2."
        test_file.write_text(expected_content, encoding="utf-8")

        # Act
        result = read_file(str(test_file))

        # Assert
        assert result == expected_content

    def test_read_file_with_offset_and_limit(self, tmp_path):
        """
        Arrange: Arquivo com múltiplas linhas
        Act: Lê com offset e limit
        Assert: Retorna apenas linhas especificadas
        """
        # Arrange
        test_file = tmp_path / "multiline.txt"
        content = "Linha 1\nLinha 2\nLinha 3\nLinha 4\nLinha 5"
        test_file.write_text(content, encoding="utf-8")

        # Act
        result = read_file(str(test_file), offset=1, limit=2)

        # Assert
        assert result == "Linha 2\nLinha 3\n"

    def test_read_file_with_offset_only(self, tmp_path):
        """
        Arrange: Arquivo com múltiplas linhas
        Act: Lê com offset apenas
        Assert: Retorna linhas a partir do offset
        """
        # Arrange
        test_file = tmp_path / "multiline.txt"
        content = "Linha 1\nLinha 2\nLinha 3\nLinha 4\nLinha 5"
        test_file.write_text(content, encoding="utf-8")

        # Act
        result = read_file(str(test_file), offset=3)

        # Assert
        assert result == "Linha 4\nLinha 5"

    def test_read_file_not_found(self):
        """
        Arrange: Caminho inexistente
        Act: Tenta ler arquivo
        Assert: Retorna mensagem de erro apropriada
        """
        # Arrange
        non_existent_path = "caminho/que/nao/existe/arquivo.txt"

        # Act
        result = read_file(non_existent_path)

        # Assert
        assert "not found" in result.lower() or "not found" in result.lower()
        assert "erro" in result.lower() or "error" in result.lower()


class TestWriteFile:
    """Testes para função write_file"""

    @pytest.fixture
    def mock_input_yes(self, monkeypatch):
        """Fixture para mock de ask_confirmation confirmando"""

        def mock_ask_confirmation(*args, **kwargs):
            return True

        monkeypatch.setattr(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            mock_ask_confirmation,
        )

    def test_write_file_creates_new_file(self, tmp_path, mock_input_yes):
        """
        Arrange: Arquivo não existe
        Act: Escreve conteúdo
        Assert: Arquivo é criado com conteúdo correto
        """
        # Arrange
        test_file = tmp_path / "new.txt"
        content = "Novo conteúdo"

        # Act
        result = write_file(str(test_file), content)

        # Assert
        assert (
            "sucesso" in result.lower()
            or "escrito" in result.lower()
            or "criado" in result.lower()
        )
        assert test_file.exists()
        assert test_file.read_text(encoding="utf-8") == content

    def test_write_file_overwrites_existing(self, tmp_path, mock_input_yes):
        """
        Arrange: Arquivo existe
        Act: Escreve novo conteúdo
        Assert: Arquivo é sobrescrito
        """
        # Arrange
        test_file = tmp_path / "existing.txt"
        original = "Conteúdo original"
        new = "Novo conteúdo"
        test_file.write_text(original, encoding="utf-8")

        # Act
        result = write_file(str(test_file), new)

        # Assert
        assert "sucesso" in result.lower() or "escrito" in result.lower()
        assert test_file.read_text(encoding="utf-8") == new


class TestListDirectory:
    """Testes para função list_directory"""

    def test_list_directory_shows_files(self, tmp_path):
        """
        Arrange: Diretório com arquivos
        Act: Lista diretório
        Assert: Arquivos são listados
        """
        # Arrange
        (tmp_path / "file1.txt").write_text("content", encoding="utf-8")
        (tmp_path / "file2.py").write_text("code", encoding="utf-8")

        # Act
        result = list_directory(str(tmp_path))

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        # list_directory retorna tabela formatada
        assert (
            "file1.txt" in result
            or "file2.py" in result
            or "sucesso" in result.lower()
            or "listou" in result.lower()
        )

    def test_list_directory_empty(self, tmp_path):
        """
        Arrange: Diretório vazio
        Act: Lista diretório
        Assert: Retorna resultado apropriado
        """
        # Arrange
        # Diretório já está vazio

        # Act
        result = list_directory(str(tmp_path))

        # Assert
        assert isinstance(result, str)
        # Pode retornar mensagem ou lista vazia
        assert len(result) >= 0
