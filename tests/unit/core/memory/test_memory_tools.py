"""Tests for memory_tools.py - Memory/notebook tools."""

from pathlib import Path
from unittest.mock import Mock, patch

from aura_cli.core.tools.memory_tools import (
    info_sessao_caderno,
    ler_pagina_caderno,
    listar_paginas_caderno,
    save_constitution,
    ver_indice_caderno,
)


class TestLerPaginaCaderno:
    """Test suite for ler_pagina_caderno."""

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_ler_pagina_success(self, mock_stats, mock_display, mock_notebook):
        """Test reading page successfully."""
        mock_notebook.read_page.return_value = "# Snapshot\n\nContent here"
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = ler_pagina_caderno(".aura/notebooks/session/pagina_001.txt")

        assert "Snapshot" in result
        assert "Content here" in result
        mock_notebook.read_page.assert_called_once()

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_ler_pagina_error(self, mock_stats, mock_display, mock_notebook):
        """Test reading page with error."""
        mock_notebook.read_page.return_value = "ERRO: File not found"
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = ler_pagina_caderno("invalid_path.txt")

        assert "ERRO" in result
        mock_notebook.read_page.assert_called_once()

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_ler_pagina_exception(self, mock_stats, mock_display, mock_notebook):
        """Test reading page with exception."""
        mock_notebook.read_page.side_effect = Exception("IO Error")
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = ler_pagina_caderno("test.txt")

        assert "erro" in result.lower() or "error" in result.lower()


class TestListarPaginasCaderno:
    """Test suite for listar_paginas_caderno."""

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_listar_paginas_with_pages(
        self, mock_stats, mock_display, mock_notebook, tmp_path
    ):
        """Test listing pages when pages exist."""
        mock_notebook.list_pages.return_value = ["pagina_001.txt", "pagina_002.txt"]
        mock_notebook.get_session_info.return_value = {"total_size_bytes": 2048}
        mock_notebook.session_id = "test_session"
        mock_notebook.session_path = tmp_path
        (tmp_path / "pagina_001.txt").write_text("x" * 1024)
        (tmp_path / "pagina_002.txt").write_text("x" * 1024)

        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = listar_paginas_caderno()

        assert "test_session" in result
        assert "pagina_001.txt" in result
        assert "pagina_002.txt" in result
        assert "2" in result  # Total pages

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_listar_paginas_no_pages(self, mock_stats, mock_display, mock_notebook):
        """Test listing pages when no pages exist."""
        mock_notebook.list_pages.return_value = []
        mock_notebook.session_id = "test_session"
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = listar_paginas_caderno()

        assert "nenhuma página" in result.lower() or "no pages" in result.lower()
        assert "test_session" in result

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_listar_paginas_exception(self, mock_stats, mock_display, mock_notebook):
        """Test listing pages with exception."""
        mock_notebook.list_pages.side_effect = Exception("Error")
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = listar_paginas_caderno()

        assert "erro" in result.lower() or "error" in result.lower()


class TestVerIndiceCaderno:
    """Test suite for ver_indice_caderno."""

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_ver_indice_with_index(self, mock_stats, mock_display, mock_notebook):
        """Test viewing index when index exists."""
        mock_notebook.read_index.return_value = (
            "# Índice do Caderno\n\n## Page 1\nContent"
        )
        mock_notebook.session_id = "test_session"
        mock_notebook.session_path = Path("/test/path")
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = ver_indice_caderno()

        assert "test_session" in result
        assert "Page 1" in result or "Página" in result

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_ver_indice_empty(self, mock_stats, mock_display, mock_notebook):
        """Test viewing index when empty."""
        mock_notebook.read_index.return_value = "# Índice do Caderno"
        mock_notebook.session_id = "test_session"
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = ver_indice_caderno()

        assert "nenhuma página" in result.lower() or "no pages" in result.lower()
        assert "test_session" in result

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_ver_indice_exception(self, mock_stats, mock_display, mock_notebook):
        """Test viewing index with exception."""
        mock_notebook.read_index.side_effect = Exception("Error")
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = ver_indice_caderno()

        assert "erro" in result.lower() or "error" in result.lower()


class TestInfoSessaoCaderno:
    """Test suite for info_sessao_caderno."""

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_info_sessao_success(self, mock_stats, mock_display, mock_notebook):
        """Test getting session info successfully."""
        mock_notebook.get_session_info.return_value = {
            "page_count": 5,
            "total_size_bytes": 5120,
        }
        mock_notebook.session_id = "test_session"
        mock_notebook.session_path = Path("/test/path")
        mock_notebook._lib = None
        mock_notebook.page_counter = 5
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = info_sessao_caderno()

        assert "test_session" in result
        assert "5" in result  # page_count
        assert "KB" in result or "5.0 KB" in result

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_info_sessao_with_nim_backend(
        self, mock_stats, mock_display, mock_notebook
    ):
        """Test getting session info with Nim backend."""
        mock_notebook.get_session_info.return_value = {
            "page_count": 3,
            "total_size_bytes": 1024,
        }
        mock_notebook.session_id = "test_session"
        mock_notebook.session_path = Path("/test/path")
        mock_notebook._lib = Mock()  # Nim backend available
        mock_notebook.page_counter = 3
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = info_sessao_caderno()

        assert "Nim" in result or "nim" in result

    @patch("aura_cli.core.tools.memory_tools.notebook_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_info_sessao_exception(self, mock_stats, mock_display, mock_notebook):
        """Test getting session info with exception."""
        mock_notebook.get_session_info.side_effect = Exception("Error")
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = info_sessao_caderno()

        assert "erro" in result.lower() or "error" in result.lower()


class TestSaveConstitution:
    """Test suite for save_constitution."""

    @patch("aura_cli.core.memory.memory_service.get_memory_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_save_constitution_success(self, mock_stats, mock_display, mock_memory):
        """Test saving constitution successfully."""
        mock_memory_instance = Mock()
        mock_memory_instance.save_constitution = Mock(return_value=True)
        mock_memory.return_value = mock_memory_instance
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = save_constitution("# Constitution\n\nRules here")

        assert "sucesso" in result.lower() or "success" in result.lower()
        mock_memory_instance.save_constitution.assert_called_once()

    @patch("aura_cli.core.memory.memory_service.get_memory_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_save_constitution_failure(self, mock_stats, mock_display, mock_memory):
        """Test saving constitution with failure."""
        mock_memory_instance = Mock()
        mock_memory_instance.save_constitution = Mock(return_value=False)
        mock_memory.return_value = mock_memory_instance
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = save_constitution("# Constitution\n\nRules here")

        assert (
            "erro" in result.lower()
            or "error" in result.lower()
            or "falha" in result.lower()
        )

    @patch("aura_cli.core.memory.memory_service.get_memory_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_save_constitution_exception(self, mock_stats, mock_display, mock_memory):
        """Test saving constitution with exception."""
        mock_memory.side_effect = Exception("Memory error")
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = save_constitution("# Constitution\n\nRules here")

        assert "erro" in result.lower() or "error" in result.lower()

    @patch("aura_cli.core.memory.memory_service.get_memory_service")
    @patch("aura_cli.core.ui.display_tool_call")
    @patch("aura_cli.core.tools.memory_tools.get_stats")
    def test_save_constitution_custom_root(self, mock_stats, mock_display, mock_memory):
        """Test saving constitution with custom project root."""
        mock_memory_instance = Mock()
        mock_memory_instance.save_constitution = Mock(return_value=True)
        mock_memory.return_value = mock_memory_instance
        mock_stats_instance = Mock()
        mock_stats.return_value = mock_stats_instance

        result = save_constitution("# Constitution", project_root="/custom/path")

        assert "sucesso" in result.lower() or "success" in result.lower()
        # Verify custom path was used
        mock_memory.assert_called_once()
