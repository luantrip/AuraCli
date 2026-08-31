"""Tests for Paint Background Extension.

Tests background art generation for agents.
"""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_llm_client():
    """Mock LLM client."""
    client = AsyncMock()
    client.query = AsyncMock()
    return client


@pytest.fixture
def paint_extension(mock_llm_client):
    """Create PaintBackgroundExtension instance."""
    from extensions.paint_background_extension import PaintBackgroundExtension

    return PaintBackgroundExtension(mock_llm_client)


class TestPaintBackgroundExtension:
    """Test PaintBackgroundExtension functionality."""

    @pytest.mark.asyncio
    async def test_generate_ascii(self, paint_extension, mock_llm_client):
        """Test ASCII art generation."""
        mock_llm_client.query.return_value = "█" * 80 + "\n" + " " * 80

        result = await paint_extension.generate("test logo", width=80, height=2)

        assert "art" in result
        assert result["mode"] == "auto"
        assert result["cached"] is False

    @pytest.mark.asyncio
    async def test_cache_functionality(self, paint_extension, mock_llm_client):
        """Test caching of generated art."""
        mock_llm_client.query.return_value = "█" * 80

        # First call - not cached
        result1 = await paint_extension.generate("logo", width=80, height=10)
        assert result1["cached"] is False

        # Second call - cached
        result2 = await paint_extension.generate("logo", width=80, height=10)
        assert result2["cached"] is True
        assert result2["art"] == result1["art"]

    @pytest.mark.asyncio
    async def test_different_sizes_not_cached(self, paint_extension, mock_llm_client):
        """Test that different sizes are not cached together."""
        mock_llm_client.query.return_value = "█" * 80

        result1 = await paint_extension.generate("logo", width=80, height=10)
        result2 = await paint_extension.generate("logo", width=40, height=5)

        assert result1["cached"] is False
        assert result2["cached"] is False

    def test_clear_cache(self, paint_extension):
        """Test cache clearing."""
        paint_extension._cache["test"] = "data"
        assert len(paint_extension._cache) == 1

        paint_extension.clear_cache()
        assert len(paint_extension._cache) == 0

    def test_cache_stats(self, paint_extension):
        """Test cache statistics."""
        paint_extension._cache["test1"] = "data1"
        paint_extension._cache["test2"] = "data2"

        stats = paint_extension.get_cache_stats()
        assert stats["cached_items"] == 2
        assert "temp_dir" in stats

    @pytest.mark.asyncio
    async def test_file_saving(self, paint_extension, mock_llm_client):
        """Test that generated art is saved to file."""
        mock_llm_client.query.return_value = "█" * 80

        result = await paint_extension.generate("logo", width=80, height=10)

        assert "file" in result
        file_path = Path(result["file"])
        assert file_path.exists()
        assert file_path.read_text() == result["art"]

    @pytest.mark.asyncio
    async def test_error_handling(self, paint_extension, mock_llm_client):
        """Test error handling."""
        mock_llm_client.query.side_effect = Exception("LLM error")

        result = await paint_extension.generate("test")

        assert "error" in result

    @pytest.mark.asyncio
    async def test_primitives_mode(self, paint_extension, mock_llm_client):
        """Test primitives generation mode."""
        mock_llm_client.query.return_value = """
        {
            "shapes": [
                {"type": "circle", "x": 10, "y": 10, "radius": 5, "char": "○"}
            ]
        }
        """

        result = await paint_extension.generate("circle", mode="primitives")

        assert "art" in result
        assert "○" in result["art"]


class TestHelperFunctions:
    """Test helper functions."""

    @pytest.mark.asyncio
    async def test_generate_ascii_art(self, mock_llm_client):
        """Test generate_ascii_art helper."""
        with patch(
            "extensions.paint_background_extension.get_paint_extension"
        ) as mock_get:
            mock_ext = MagicMock()
            mock_ext.generate = AsyncMock(return_value={"art": "test art"})
            mock_get.return_value = mock_ext

            from extensions.paint_background_extension import generate_ascii_art

            art = await generate_ascii_art("logo")

            assert art == "test art"

    @pytest.mark.asyncio
    async def test_generate_icon(self, mock_llm_client):
        """Test generate_icon helper."""
        with patch(
            "extensions.paint_background_extension.generate_ascii_art"
        ) as mock_gen:
            mock_gen.return_value = "★"

            from extensions.paint_background_extension import generate_icon

            icon = await generate_icon("star", size=5)

            assert icon == "★"
            mock_gen.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_logo(self, mock_llm_client):
        """Test generate_logo helper."""
        with patch(
            "extensions.paint_background_extension.generate_ascii_art"
        ) as mock_gen:
            mock_gen.return_value = "LOGO"

            from extensions.paint_background_extension import generate_logo

            logo = await generate_logo("AURA")

            assert logo == "LOGO"
            mock_gen.assert_called_once()


class TestCanvasRendering:
    """Test canvas rendering functions."""

    def test_render_circle_to_canvas(self, paint_extension):
        """Test circle rendering to text canvas."""
        canvas = [[" " for _ in range(20)] for _ in range(20)]
        shape = {"type": "circle", "x": 10, "y": 10, "radius": 3, "char": "○"}

        paint_extension._render_shape_to_canvas(canvas, shape, 20, 20)

        # Check center is filled
        assert canvas[10][10] == "○"

    def test_render_line_to_canvas(self, paint_extension):
        """Test line rendering to text canvas."""
        canvas = [[" " for _ in range(20)] for _ in range(20)]
        shape = {"type": "line", "x1": 0, "y1": 0, "x2": 10, "y2": 10, "char": "█"}

        paint_extension._render_shape_to_canvas(canvas, shape, 20, 20)

        # Check endpoints
        assert canvas[0][0] == "█"
        assert canvas[10][10] == "█"

    def test_render_text_to_canvas(self, paint_extension):
        """Test text rendering to text canvas."""
        canvas = [[" " for _ in range(20)] for _ in range(20)]
        shape = {"type": "text", "x": 5, "y": 5, "text": "Hi"}

        paint_extension._render_shape_to_canvas(canvas, shape, 20, 20)

        # Check text
        assert canvas[5][5] == "H"
        assert canvas[5][6] == "i"
