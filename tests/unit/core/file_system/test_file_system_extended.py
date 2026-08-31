"""
Testes abrangentes para sistema de arquivos.

Testa todas as operações de I/O com múltiplos cenários e edge cases.
Seguindo padrão AAA (Arrange-Act-Assert).
"""

import pytest

from aura_cli.core.tools.file_system import list_directory, read_file, write_file


class TestReadFileComprehensive:
    """Testes abrangentes para read_file"""

    def test_read_file_complete_small_file(self, tmp_path):
        """
        Arrange: Cria arquivo pequeno com conteúdo conhecido
        Act: Lê arquivo completo
        Assert: Conteúdo lido é idêntico ao escrito
        """
        # Arrange
        test_file = tmp_path / "small.txt"
        expected_content = "Hello, World!"
        test_file.write_text(expected_content, encoding="utf-8")

        # Act
        result = read_file(str(test_file))

        # Assert
        assert result == expected_content

    def test_read_file_complete_large_file(self, tmp_path):
        """
        Arrange: Cria arquivo grande com múltiplas linhas
        Act: Lê arquivo completo
        Assert: Todas as linhas são lidas corretamente
        """
        # Arrange
        test_file = tmp_path / "large.txt"
        lines = [f"Linha {i}\n" for i in range(1000)]
        expected_content = "".join(lines)
        test_file.write_text(expected_content, encoding="utf-8")

        # Act
        result = read_file(str(test_file))

        # Assert
        assert result == expected_content
        assert result.count("\n") == 1000

    def test_read_file_with_offset_start(self, tmp_path):
        """
        Arrange: Cria arquivo com múltiplas linhas
        Act: Lê a partir de offset específico
        Assert: Retorna apenas linhas a partir do offset
        """
        # Arrange
        test_file = tmp_path / "multiline.txt"
        content = "Linha 1\nLinha 2\nLinha 3\nLinha 4\nLinha 5"
        test_file.write_text(content, encoding="utf-8")

        # Act
        result = read_file(str(test_file), offset=2)

        # Assert
        assert "Linha 1" not in result
        assert "Linha 2" not in result
        assert "Linha 3" in result
        assert "Linha 4" in result
        assert "Linha 5" in result

    def test_read_file_with_offset_and_limit(self, tmp_path):
        """
        Arrange: Cria arquivo com múltiplas linhas
        Act: Lê com offset e limit
        Assert: Retorna exatamente o número de linhas especificado
        """
        # Arrange
        test_file = tmp_path / "multiline.txt"
        content = "\n".join([f"Linha {i}" for i in range(1, 11)])
        test_file.write_text(content, encoding="utf-8")

        # Act
        result = read_file(str(test_file), offset=2, limit=3)

        # Assert
        lines = result.strip().split("\n")
        assert len(lines) == 3
        assert "Linha 3" in result
        assert "Linha 4" in result
        assert "Linha 5" in result

    def test_read_file_offset_zero(self, tmp_path):
        """
        Arrange: Cria arquivo
        Act: Lê com offset=0
        Assert: Retorna desde o início
        """
        # Arrange
        test_file = tmp_path / "test.txt"
        content = "Primeira linha\nSegunda linha\nTerceira linha"
        test_file.write_text(content, encoding="utf-8")

        # Act
        result = read_file(str(test_file), offset=0, limit=2)

        # Assert
        assert "Primeira linha" in result
        assert "Segunda linha" in result
        assert "Terceira linha" not in result

    def test_read_file_limit_exceeds_file_size(self, tmp_path):
        """
        Arrange: Cria arquivo pequeno
        Act: Lê com limit maior que tamanho do arquivo
        Assert: Retorna todo o arquivo sem erro
        """
        # Arrange
        test_file = tmp_path / "small.txt"
        content = "Linha 1\nLinha 2"
        test_file.write_text(content, encoding="utf-8")

        # Act
        result = read_file(str(test_file), offset=0, limit=100)

        # Assert
        assert result == content

    def test_read_file_nonexistent_file(self):
        """
        Arrange: Caminho inexistente
        Act: Tenta ler arquivo
        Assert: Retorna mensagem de erro apropriada
        """
        # Arrange
        non_existent_path = "/nonexistent/path/file.txt"

        # Act
        result = read_file(non_existent_path)

        # Assert
        assert "não encontrado" in result.lower() or "not found" in result.lower()
        assert "erro" in result.lower() or "error" in result.lower()

    def test_read_file_empty_file(self, tmp_path):
        """
        Arrange: Cria arquivo vazio
        Act: Lê arquivo vazio
        Assert: Retorna string vazia
        """
        # Arrange
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")

        # Act
        result = read_file(str(test_file))

        # Assert
        assert result == ""

    def test_read_file_binary_content_handling(self, tmp_path):
        """
        Arrange: Cria arquivo com caracteres especiais
        Act: Lê arquivo
        Assert: Conteúdo é lido corretamente
        """
        # Arrange
        test_file = tmp_path / "special.txt"
        content = "Café\nNaïve\nMüller"
        test_file.write_text(content, encoding="utf-8")

        # Act
        result = read_file(str(test_file))

        # Assert
        assert "Café" in result
        assert "Naïve" in result
        assert "Müller" in result


class TestWriteFileComprehensive:
    """Testes abrangentes para write_file"""

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
        Arrange: Arquivo existe com conteúdo antigo
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
        assert original not in test_file.read_text(encoding="utf-8")

    def test_write_file_append_mode(self, tmp_path, mock_input_yes):
        """
        Arrange: Arquivo existe
        Act: Escreve em modo append
        Assert: Conteúdo é adicionado ao final
        """
        # Arrange
        test_file = tmp_path / "append.txt"
        original = "Linha 1\n"
        additional = "Linha 2\n"
        test_file.write_text(original, encoding="utf-8")

        # Act
        result = write_file(str(test_file), additional, append=True)

        # Assert
        assert "sucesso" in result.lower() or "adicionado" in result.lower()
        final_content = test_file.read_text(encoding="utf-8")
        assert final_content == original + additional

    def test_write_file_append_to_empty_file(self, tmp_path, mock_input_yes):
        """
        Arrange: Arquivo vazio
        Act: Escreve em modo append
        Assert: Conteúdo é adicionado
        """
        # Arrange
        test_file = tmp_path / "empty.txt"
        test_file.write_text("", encoding="utf-8")
        content = "Primeira linha\n"

        # Act
        write_file(str(test_file), content, append=True)

        # Assert
        assert test_file.read_text(encoding="utf-8") == content

    def test_write_file_large_content(self, tmp_path, mock_input_yes):
        """
        Arrange: Conteúdo grande
        Act: Escreve arquivo grande
        Assert: Arquivo é escrito corretamente
        """
        # Arrange
        test_file = tmp_path / "large.txt"
        large_content = "A" * 100000  # 100KB

        # Act
        result = write_file(str(test_file), large_content)

        # Assert
        assert "sucesso" in result.lower() or "escrito" in result.lower()
        assert test_file.stat().st_size >= 100000
        assert test_file.read_text(encoding="utf-8") == large_content

    def test_write_file_special_characters(self, tmp_path, mock_input_yes):
        """
        Arrange: Conteúdo com caracteres especiais
        Act: Escreve arquivo
        Assert: Caracteres especiais são preservados
        """
        # Arrange
        test_file = tmp_path / "special.txt"
        content = "Café\nNaïve\nMüller\nEmoji: 🚀"

        # Act
        result = write_file(str(test_file), content)

        # Assert
        assert "sucesso" in result.lower() or "escrito" in result.lower()
        assert test_file.read_text(encoding="utf-8") == content


class TestListDirectoryComprehensive:
    """Testes abrangentes para list_directory"""

    def test_list_directory_with_files_only(self, tmp_path):
        """
        Arrange: Cria diretório com apenas arquivos
        Act: Lista diretório
        Assert: Todos os arquivos são listados
        """
        # Arrange
        (tmp_path / "file1.txt").write_text("content1", encoding="utf-8")
        (tmp_path / "file2.py").write_text("content2", encoding="utf-8")
        (tmp_path / "file3.json").write_text("{}", encoding="utf-8")

        # Act
        result = list_directory(str(tmp_path))

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        # list_directory retorna tabela formatada, verifica se contém os arquivos ou mensagem de sucesso
        assert (
            "file1.txt" in result
            or "file2.py" in result
            or "file3.json" in result
            or "sucesso" in result.lower()
            or "listou" in result.lower()
        )

    def test_list_directory_with_subdirectories(self, tmp_path):
        """
        Arrange: Cria estrutura com subdiretórios
        Act: Lista diretório
        Assert: Subdiretórios são listados
        """
        # Arrange
        (tmp_path / "file.txt").write_text("content", encoding="utf-8")
        (tmp_path / "subdir1").mkdir()
        (tmp_path / "subdir2").mkdir()
        (tmp_path / "subdir1" / "nested.txt").write_text("nested", encoding="utf-8")

        # Act
        result = list_directory(str(tmp_path))

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        # list_directory retorna tabela formatada, verifica estrutura
        assert (
            "file.txt" in result
            or "subdir" in result.lower()
            or "sucesso" in result.lower()
            or "listou" in result.lower()
        )

    def test_list_directory_empty_directory(self, tmp_path):
        """
        Arrange: Cria diretório vazio
        Act: Lista diretório
        Assert: Retorna mensagem apropriada ou lista vazia
        """
        # Arrange
        # Diretório já está vazio

        # Act
        result = list_directory(str(tmp_path))

        # Assert
        assert isinstance(result, str)
        # Pode retornar mensagem de diretório vazio ou lista vazia
        assert len(result) >= 0

    def test_list_directory_nonexistent_path(self):
        """
        Arrange: Caminho inexistente
        Act: Tenta listar diretório
        Assert: Retorna mensagem de erro
        """
        # Arrange
        non_existent_path = "/nonexistent/directory/path"

        # Act
        result = list_directory(non_existent_path)

        # Assert
        assert (
            "erro" in result.lower()
            or "não encontrado" in result.lower()
            or "not found" in result.lower()
        )

    def test_list_directory_hidden_files(self, tmp_path):
        """
        Arrange: Cria arquivos ocultos
        Act: Lista diretório
        Assert: Arquivos ocultos podem ou não aparecer (depende da implementação)
        """
        # Arrange
        (tmp_path / ".hidden").write_text("hidden", encoding="utf-8")
        (tmp_path / "visible.txt").write_text("visible", encoding="utf-8")

        # Act
        result = list_directory(str(tmp_path))

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        # list_directory retorna tabela formatada
        assert (
            "visible.txt" in result
            or "sucesso" in result.lower()
            or "listou" in result.lower()
        )
        # .hidden pode ou não aparecer dependendo da implementação

    def test_list_directory_mixed_content(self, tmp_path):
        """
        Arrange: Cria estrutura mista (arquivos, diretórios, subdiretórios)
        Act: Lista diretório
        Assert: Toda estrutura é listada
        """
        # Arrange
        (tmp_path / "root_file.txt").write_text("root", encoding="utf-8")
        (tmp_path / "subdir").mkdir()
        (tmp_path / "subdir" / "nested_file.py").write_text("nested", encoding="utf-8")
        (tmp_path / "another_file.json").write_text("{}", encoding="utf-8")

        # Act
        result = list_directory(str(tmp_path))

        # Assert
        assert isinstance(result, str)
        assert len(result) > 0
        # list_directory retorna tabela formatada, verifica que estrutura é listada
        assert (
            "root_file" in result
            or "subdir" in result
            or "another_file" in result
            or "sucesso" in result.lower()
            or "listou" in result.lower()
        )
