"""Tests for Paint Tools - paint_generate_art function."""

from unittest.mock import MagicMock, patch

import pytest

from aura_cli.core.tools.paint_tools import paint_generate_art


@pytest.fixture
def temp_artes_dir(tmp_path):
    artes_dir = tmp_path / "artes"
    artes_dir.mkdir()
    return artes_dir


def _mock_asyncio(gen_result):
    """Return a context manager that mocks asyncio.get_event_loop().run_until_complete."""
    mock_asyncio = MagicMock()
    mock_loop = MagicMock()
    mock_loop.is_running.return_value = False
    mock_loop.run_until_complete.return_value = gen_result
    mock_asyncio.get_event_loop.return_value = mock_loop
    return mock_asyncio


def _make_agent(gen_result, save_result):
    agent = MagicMock()
    agent.generate_art = MagicMock(return_value=gen_result)
    agent.save = MagicMock(return_value=save_result)
    return agent


class TestPaintGenerateArt:
    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_success(
        self, mock_get_llm, mock_agent_class, mock_asyncio, temp_artes_dir
    ):
        gen_result = {"success": True, "width": 80, "height": 24}
        save_result = {
            "success": True,
            "file_path": str(temp_artes_dir / "test.ans"),
            "size": 1000,
        }
        mock_agent_class.return_value = _make_agent(gen_result, save_result)
        mock_get_llm.return_value = MagicMock()
        mock_asyncio.get_event_loop.return_value = MagicMock(
            is_running=MagicMock(return_value=False),
            run_until_complete=MagicMock(return_value=gen_result),
        )

        result = paint_generate_art(
            prompt="a cat",
            width=80,
            height=24,
            output_file=str(temp_artes_dir / "test.ans"),
            output_format="ans",
        )

        assert result["success"] is True
        assert "file_path" in result
        assert result["format"] == "ans"
        assert result["width"] == 80
        assert result["height"] == 24

    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_default_output(
        self, mock_get_llm, mock_agent_class, mock_asyncio, tmp_path
    ):
        gen_result = {"success": True, "width": 80, "height": 24}
        save_result = {
            "success": True,
            "file_path": str(tmp_path / "artes" / "arte_123.ans"),
            "size": 1000,
        }
        mock_agent_class.return_value = _make_agent(gen_result, save_result)
        mock_get_llm.return_value = MagicMock()
        mock_asyncio.get_event_loop.return_value = MagicMock(
            is_running=MagicMock(return_value=False),
            run_until_complete=MagicMock(return_value=gen_result),
        )

        with patch("time.time", return_value=123):
            result = paint_generate_art(prompt="a cat")

        assert result["success"] is True
        assert "file_path" in result

    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_different_formats(
        self, mock_get_llm, mock_agent_class, mock_asyncio, temp_artes_dir
    ):
        for fmt in ["ans", "png", "svg", "html"]:
            gen_result = {"success": True, "width": 80, "height": 24}
            save_result = {
                "success": True,
                "file_path": str(temp_artes_dir / f"test.{fmt}"),
                "size": 1000,
            }
            mock_agent_class.return_value = _make_agent(gen_result, save_result)
            mock_get_llm.return_value = MagicMock()
            mock_asyncio.get_event_loop.return_value = MagicMock(
                is_running=MagicMock(return_value=False),
                run_until_complete=MagicMock(return_value=gen_result),
            )

            result = paint_generate_art(
                prompt="test",
                output_file=str(temp_artes_dir / f"test.{fmt}"),
                output_format=fmt,
            )

            assert result["success"] is True
            assert result["format"] == fmt

    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_generation_failure(
        self, mock_get_llm, mock_agent_class, mock_asyncio
    ):
        gen_result = {"success": False, "error": "Generation failed"}
        mock_agent_class.return_value = _make_agent(gen_result, {})
        mock_get_llm.return_value = MagicMock()
        mock_asyncio.get_running_loop.side_effect = RuntimeError("no running loop")
        mock_asyncio.run.return_value = gen_result

        result = paint_generate_art(prompt="test")

        assert result["success"] is False
        assert "error" in result
        assert result["file_path"] is None

    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_save_failure(
        self, mock_get_llm, mock_agent_class, mock_asyncio, temp_artes_dir
    ):
        gen_result = {"success": True, "width": 80, "height": 24}
        save_result = {"success": False, "error": "Save failed"}
        mock_agent_class.return_value = _make_agent(gen_result, save_result)
        mock_get_llm.return_value = MagicMock()
        mock_asyncio.get_event_loop.return_value = MagicMock(
            is_running=MagicMock(return_value=False),
            run_until_complete=MagicMock(return_value=gen_result),
        )

        result = paint_generate_art(
            prompt="test", output_file=str(temp_artes_dir / "test.ans")
        )

        assert result["success"] is False
        assert "error" in result

    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_no_llm_client(
        self, mock_get_llm, mock_agent_class, mock_asyncio
    ):
        """LLM unavailable — agent still runs with llm_client=None."""
        mock_get_llm.side_effect = Exception("No LLM available")
        gen_result = {"success": True, "width": 80, "height": 24}
        save_result = {"success": True, "file_path": "artes/test.ans", "size": 1000}
        mock_agent_class.return_value = _make_agent(gen_result, save_result)
        mock_asyncio.get_event_loop.return_value = MagicMock(
            is_running=MagicMock(return_value=False),
            run_until_complete=MagicMock(return_value=gen_result),
        )

        result = paint_generate_art(prompt="test")

        assert result["success"] is True

    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_exception_handling(self, mock_get_llm, mock_agent_class):
        """Agent creation failure returns error dict."""
        mock_get_llm.side_effect = Exception("Unexpected error")
        mock_agent_class.side_effect = Exception("Agent creation failed")

        result = paint_generate_art(prompt="test")

        assert result["success"] is False
        assert "error" in result

    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_different_modes(
        self, mock_get_llm, mock_agent_class, mock_asyncio, temp_artes_dir
    ):
        for mode in ["auto", "ascii", "primitives", "hybrid"]:
            gen_result = {"success": True, "width": 80, "height": 24}
            save_result = {
                "success": True,
                "file_path": str(temp_artes_dir / "test.ans"),
                "size": 1000,
            }
            mock_agent_class.return_value = _make_agent(gen_result, save_result)
            mock_get_llm.return_value = MagicMock()
            mock_asyncio.get_event_loop.return_value = MagicMock(
                is_running=MagicMock(return_value=False),
                run_until_complete=MagicMock(return_value=gen_result),
            )

            result = paint_generate_art(
                prompt="test",
                output_file=str(temp_artes_dir / "test.ans"),
                mode=mode,
            )

            assert result["success"] is True

    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_generate_art_custom_dimensions(
        self, mock_get_llm, mock_agent_class, mock_asyncio, temp_artes_dir
    ):
        gen_result = {"success": True, "width": 120, "height": 40}
        save_result = {
            "success": True,
            "file_path": str(temp_artes_dir / "test.ans"),
            "size": 2000,
        }
        mock_agent_class.return_value = _make_agent(gen_result, save_result)
        mock_get_llm.return_value = MagicMock()
        mock_asyncio.get_event_loop.return_value = MagicMock(
            is_running=MagicMock(return_value=False),
            run_until_complete=MagicMock(return_value=gen_result),
        )

        result = paint_generate_art(
            prompt="test",
            width=120,
            height=40,
            output_file=str(temp_artes_dir / "test.ans"),
        )

        assert result["success"] is True
        assert result["width"] == 120
        assert result["height"] == 40


class TestPaintGenerateArtIntegration:
    @patch("aura_cli.core.tools.paint_tools.asyncio")
    @patch("aura_cli.core.tools.paint_tools.HeadlessPaintAgent")
    @patch("aura_cli.core.llm.base.get_llm_client")
    def test_full_generation_flow(
        self, mock_get_llm, mock_agent_class, mock_asyncio, tmp_path
    ):
        artes_dir = tmp_path / "artes"
        artes_dir.mkdir()
        output_file = artes_dir / "test.ans"

        gen_result = {"success": True, "width": 40, "height": 10}
        save_result = {"success": True, "file_path": str(output_file), "size": 500}
        mock_agent_class.return_value = _make_agent(gen_result, save_result)
        mock_get_llm.return_value = MagicMock()
        mock_asyncio.get_event_loop.return_value = MagicMock(
            is_running=MagicMock(return_value=False),
            run_until_complete=MagicMock(return_value=gen_result),
        )

        result = paint_generate_art(
            prompt="simple test",
            width=40,
            height=10,
            output_file=str(output_file),
            output_format="ans",
        )

        assert result["success"] is True
        assert result["file_path"] == str(output_file)
        assert result["format"] == "ans"
