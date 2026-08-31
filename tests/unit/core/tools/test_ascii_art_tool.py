"""Tests for core/tools/ascii_art_tool.py."""

from unittest.mock import patch

from aura_cli.core.tools.ascii_art_tool import TOOL_METADATA, generate_ascii_art_sync


class TestGenerateAsciiArtSync:
    def test_import_error_returns_error(self):
        with patch.dict("sys.modules", {"paint_background_extension": None}):
            result = generate_ascii_art_sync("test")
        assert "[Error" in result

    def test_returns_string(self):
        # Extension may or may not be available; either way should return string
        result = generate_ascii_art_sync("test")
        assert isinstance(result, str)
        assert len(result) > 0


class TestToolMetadata:
    def test_has_required_fields(self):
        assert TOOL_METADATA["type"] == "function"
        func = TOOL_METADATA["function"]
        assert func["name"] == "generate_ascii_art"
        assert "prompt" in func["parameters"]["properties"]
        assert "prompt" in func["parameters"]["required"]

    def test_has_all_params(self):
        props = TOOL_METADATA["function"]["parameters"]["properties"]
        assert "width" in props
        assert "height" in props
        assert "mode" in props
        assert props["mode"]["enum"] == ["auto", "ascii", "primitives", "hybrid"]
