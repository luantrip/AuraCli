"""Tests for HeadlessPaintAgent - Paint Agent without TUI.

Tests the headless version of PaintAgent that works without
requiring the Paint TUI application.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aura_cli.application.paint.ansi_art_document import AnsiArtDocument
from aura_cli.core.tools.paint_agent_headless import HeadlessPaintAgent


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = AsyncMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def headless_agent(mock_llm_client):
    """Create HeadlessPaintAgent instance."""
    return HeadlessPaintAgent(
        llm_client=mock_llm_client,
        width=80,
        height=24,
    )


@pytest.fixture
def headless_agent_no_llm():
    """Create HeadlessPaintAgent without LLM."""
    return HeadlessPaintAgent(
        llm_client=None,
        width=80,
        height=24,
    )


class TestHeadlessPaintAgent:
    """Test HeadlessPaintAgent functionality."""

    def test_init_default(self):
        """Test HeadlessPaintAgent initialization with defaults."""
        agent = HeadlessPaintAgent()

        assert agent.width == 80
        assert agent.height == 24
        assert agent.llm_client is None
        assert isinstance(agent.document, AnsiArtDocument)

    def test_init_custom(self, mock_llm_client):
        """Test HeadlessPaintAgent initialization with custom params."""
        agent = HeadlessPaintAgent(
            llm_client=mock_llm_client,
            width=100,
            height=50,
            default_bg="#ffffff",
            default_fg="#000000",
        )

        assert agent.width == 100
        assert agent.height == 50
        assert agent.llm_client == mock_llm_client
        assert agent.document.width == 100
        assert agent.document.height == 50

    def test_get_document(self, headless_agent):
        """Test get_document method."""
        doc = headless_agent.get_document()

        assert isinstance(doc, AnsiArtDocument)
        assert doc.width == 80
        assert doc.height == 24

    def test_set_document(self, headless_agent):
        """Test set_document method."""
        new_doc = AnsiArtDocument(100, 50)

        headless_agent.set_document(new_doc)

        assert headless_agent.document == new_doc
        assert headless_agent.width == 100
        assert headless_agent.height == 50

    @pytest.mark.asyncio
    async def test_generate_art_llm_ascii(self, headless_agent, mock_llm_client):
        """Test art generation with LLM in ASCII mode."""
        from aura_cli.application.paint.generator import LLMPaintAgent

        with patch.object(LLMPaintAgent, "generate_art") as mock_gen:
            mock_gen.return_value = {
                "success": True,
                "content": "█" * 80 + "\n" + " " * 80,
            }

            result = await headless_agent.generate_art("test", mode="ascii")

            assert result["success"] is True
            assert "width" in result
            assert "height" in result

    @pytest.mark.asyncio
    async def test_generate_art_no_llm(self, headless_agent_no_llm):
        """Test art generation without LLM."""
        with patch.object(headless_agent_no_llm, "_get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.process_message = AsyncMock()
            mock_get_agent.return_value = mock_agent

            result = await headless_agent_no_llm.generate_art("test")

            assert result["success"] is True
            mock_agent.process_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_art_error(self, headless_agent):
        """Test error handling in art generation."""
        with patch.object(headless_agent, "_get_agent") as mock_get_agent:
            mock_agent = MagicMock()
            mock_agent.process_message = AsyncMock(
                side_effect=Exception("Generation error")
            )
            mock_get_agent.return_value = mock_agent

            result = await headless_agent.generate_art("test")

            assert result["success"] is False
            assert "error" in result

    def test_save_ans_format(self, headless_agent, tmp_path):
        """Test saving in ANSI format."""
        output_file = tmp_path / "test.ans"

        result = headless_agent.save(str(output_file), output_format="ans")

        assert result["success"] is True
        assert result["file_path"] == str(output_file.resolve())
        assert result["format"] == "ans"
        assert output_file.exists()

    def test_save_png_format(self, headless_agent, tmp_path):
        """Test saving in PNG format."""
        output_file = tmp_path / "test.png"

        result = headless_agent.save(str(output_file), output_format="png")

        assert result["success"] is True
        assert result["format"] == "png"
        assert output_file.exists()

    def test_save_svg_format(self, headless_agent, tmp_path):
        """Test saving in SVG format."""
        output_file = tmp_path / "test.svg"

        result = headless_agent.save(str(output_file), output_format="svg")

        assert result["success"] is True
        assert result["format"] == "svg"
        assert output_file.exists()

    def test_save_html_format(self, headless_agent, tmp_path):
        """Test saving in HTML format."""
        output_file = tmp_path / "test.html"

        result = headless_agent.save(str(output_file), output_format="html")

        assert result["success"] is True
        assert result["format"] == "html"
        assert output_file.exists()

    def test_save_creates_directory(self, headless_agent, tmp_path):
        """Test that save creates directory if it doesn't exist."""
        output_file = tmp_path / "new_dir" / "test.ans"

        result = headless_agent.save(str(output_file), output_format="ans")

        assert result["success"] is True
        assert output_file.parent.exists()
        assert output_file.exists()

    def test_save_error_handling(self, headless_agent):
        """Test error handling in save."""
        invalid_path = "/invalid/path/that/does/not/exist/test.ans"

        result = headless_agent.save(invalid_path, output_format="ans")

        assert result["success"] is False
        assert "error" in result

    def test_get_agent_lazy_init(self, headless_agent):
        """Test lazy initialization of agent."""
        agent1 = headless_agent._get_agent()
        agent2 = headless_agent._get_agent()

        assert agent1 is agent2
        assert headless_agent._agent is not None

    @pytest.mark.asyncio
    async def test_generate_art_auto_mode(self, headless_agent, mock_llm_client):
        """Test art generation in auto mode."""
        from aura_cli.application.paint.generator import LLMPaintAgent

        with patch.object(LLMPaintAgent, "generate_art") as mock_gen:
            mock_gen.return_value = {
                "success": True,
                "content": "test art",
            }

            result = await headless_agent.generate_art("test", mode="auto")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_art_primitives_mode(self, headless_agent, mock_llm_client):
        """Test art generation in primitives mode."""
        from aura_cli.application.paint.generator import LLMPaintAgent

        with patch.object(LLMPaintAgent, "generate_art") as mock_gen:
            mock_gen.return_value = {
                "success": True,
                "content": "test art",
            }

            result = await headless_agent.generate_art("test", mode="primitives")

            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_generate_art_hybrid_mode(self, headless_agent, mock_llm_client):
        """Test art generation in hybrid mode."""
        from aura_cli.application.paint.generator import LLMPaintAgent

        with patch.object(LLMPaintAgent, "generate_art") as mock_gen:
            mock_gen.return_value = {
                "success": True,
                "content": "test art",
            }

            result = await headless_agent.generate_art("test", mode="hybrid")

            assert result["success"] is True


class TestHeadlessPaintAgentIntegration:
    """Integration tests for HeadlessPaintAgent."""

    @pytest.mark.asyncio
    async def test_full_workflow(self, tmp_path):
        """Test complete workflow: generate and save."""
        agent = HeadlessPaintAgent(width=40, height=10)

        result = await agent.generate_art("simple test")

        assert result["success"] is True

        output_file = tmp_path / "output.ans"
        save_result = agent.save(str(output_file), output_format="ans")

        assert save_result["success"] is True
        assert output_file.exists()

    def test_document_persistence(self, headless_agent):
        """Test that document changes persist."""
        new_doc = AnsiArtDocument(100, 50)
        headless_agent.set_document(new_doc)

        assert headless_agent.get_document().width == 100
        assert headless_agent.get_document().height == 50
