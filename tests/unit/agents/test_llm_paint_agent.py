"""Tests for LLM Paint Agent.

Tests the autonomous art generation capabilities with 3 modes.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_paint_app():
    """Mock Paint application."""
    app = MagicMock()
    app.image = MagicMock()
    app.image.width = 80
    app.image.height = 24
    app.image.ch = [[" " for _ in range(80)] for _ in range(24)]
    app.image.st = [[None for _ in range(80)] for _ in range(24)]
    app.canvas = MagicMock()
    return app


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = AsyncMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def llm_agent(mock_paint_app, mock_llm_client):
    """Create LLMPaintAgent instance."""
    from aura_cli.application.paint.generator import LLMPaintAgent

    return LLMPaintAgent(mock_paint_app, mock_llm_client)


class TestLLMPaintAgent:
    """Test LLMPaintAgent functionality."""

    @pytest.mark.asyncio
    async def test_ascii_direct_generation(self, llm_agent, mock_llm_client):
        """Test ASCII direct generation mode."""
        # Mock LLM response
        mock_llm_client.query.return_value = "█" * 80 + "\n" + " " * 80

        result = await llm_agent._generate_ascii_direct("test logo")

        assert result["success"] is True
        assert result["mode"] == "ascii_direct"
        assert "art" in result
        mock_llm_client.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_primitives_generation(self, llm_agent, mock_llm_client):
        """Test primitives JSON generation mode."""
        # Mock LLM response with JSON
        mock_llm_client.query.return_value = """
        {
            "shapes": [
                {"type": "circle", "x": 10, "y": 10, "radius": 5, "color": "#FF0000"}
            ]
        }
        """

        result = await llm_agent._generate_primitives("circle")

        assert result["success"] is True
        assert result["mode"] == "primitives"
        assert "plan" in result
        assert len(result["plan"]["shapes"]) == 1

    @pytest.mark.asyncio
    async def test_hybrid_generation(self, llm_agent, mock_llm_client):
        """Test hybrid generation mode."""
        # Mock LLM response
        mock_llm_client.query.return_value = """
        {
            "background": "ASCII background",
            "shapes": [
                {"type": "line", "x1": 0, "y1": 0, "x2": 10, "y2": 10, "color": "#00FF00"}
            ]
        }
        """

        result = await llm_agent._generate_hybrid("complex scene")

        assert result["success"] is True
        assert result["mode"] == "hybrid"
        assert "plan" in result

    @pytest.mark.asyncio
    async def test_auto_mode_decision(self, llm_agent, mock_llm_client):
        """Test auto mode decision."""
        # Mock LLM to decide mode
        mock_llm_client.query.side_effect = [
            "ascii",  # Mode decision
            "█" * 80,  # Art generation
        ]

        from aura_cli.application.paint.generator import GenerationMode

        mode = await llm_agent._decide_mode("simple icon")

        assert mode == GenerationMode.ASCII_DIRECT

    @pytest.mark.asyncio
    async def test_refine_last(self, llm_agent, mock_llm_client):
        """Test refinement of last generation."""
        # First generate something
        mock_llm_client.query.return_value = "█" * 80
        await llm_agent._generate_ascii_direct("logo")

        # Then refine
        mock_llm_client.query.return_value = "▓" * 80
        result = await llm_agent.refine_last("make it darker")

        assert result["success"] is True
        assert len(llm_agent._generation_history) == 2

    def test_draw_circle_primitive(self, llm_agent):
        """Test circle primitive drawing."""
        llm_agent._draw_circle_primitive(10, 10, 5, "#FF0000", filled=True)

        # Check that pixels were set
        assert llm_agent.paint_app.image.ch[10][10] == "█"

    def test_draw_line_primitive(self, llm_agent):
        """Test line primitive drawing."""
        llm_agent._draw_line_primitive(0, 0, 10, 10, "#00FF00")

        # Check that line was drawn
        assert llm_agent.paint_app.image.ch[0][0] == "█"
        assert llm_agent.paint_app.image.ch[10][10] == "█"

    def test_draw_text_primitive(self, llm_agent):
        """Test text primitive drawing."""
        llm_agent._draw_text_primitive(5, 5, "Hello", "#FFFFFF")

        # Check that text was drawn
        assert llm_agent.paint_app.image.ch[5][5] == "H"
        assert llm_agent.paint_app.image.ch[5][6] == "e"

    @pytest.mark.asyncio
    async def test_error_handling(self, llm_agent, mock_llm_client):
        """Test error handling on LLM failure."""
        mock_llm_client.query.side_effect = Exception("LLM error")

        result = await llm_agent._generate_ascii_direct("test")

        assert result["success"] is False
        assert "error" in result

    def test_generation_history(self, llm_agent):
        """Test generation history tracking."""
        assert len(llm_agent.get_history()) == 0

        llm_agent._generation_history.append({"test": "data"})
        assert len(llm_agent.get_history()) == 1

        llm_agent.clear_history()
        assert len(llm_agent.get_history()) == 0


class TestPrimitiveDrawing:
    """Test primitive drawing functions."""

    def test_rectangle_primitive(self, llm_agent):
        """Test rectangle drawing."""
        llm_agent._draw_rectangle_primitive(0, 0, 10, 5, "#FF0000")

        # Check corners
        assert llm_agent.paint_app.image.ch[0][0] == "█"
        assert llm_agent.paint_app.image.ch[4][9] == "█"

    def test_polygon_primitive(self, llm_agent):
        """Test polygon drawing."""
        points = [[0, 0], [10, 0], [5, 10]]
        llm_agent._draw_polygon_primitive(points, "#00FF00")

        # Check that edges were drawn
        assert llm_agent.paint_app.image.ch[0][0] == "█"


class TestGenerationModes:
    """Test generation mode enum."""

    def test_mode_enum(self):
        """Test GenerationMode enum."""
        from aura_cli.application.paint.generator import GenerationMode

        assert GenerationMode.ASCII_DIRECT.value == "ascii"
        assert GenerationMode.PRIMITIVES.value == "primitives"
        assert GenerationMode.HYBRID.value == "hybrid"
        assert GenerationMode.AUTO.value == "auto"
