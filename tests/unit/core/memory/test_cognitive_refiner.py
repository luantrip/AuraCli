"""Tests for core/memory/cognitive_refiner.py."""

import json
from unittest.mock import MagicMock, patch

from aura_cli.core.memory.cognitive_refiner import (
    CognitiveRefiner,
    get_cognitive_refiner,
)


class TestCognitiveRefinerInit:
    def test_defaults(self):
        r = CognitiveRefiner()
        assert r.model is None
        assert r._refinement_cache == {}

    def test_custom_model(self):
        r = CognitiveRefiner(model="gpt-4o")
        assert r.model == "gpt-4o"


class TestEstimateTokens:
    def test_empty(self):
        r = CognitiveRefiner()
        assert r._estimate_tokens([]) == 0

    def test_estimates(self):
        r = CognitiveRefiner()
        history = [{"content": "a" * 400}]
        assert r._estimate_tokens(history) == 100  # 400/4


class TestFormatHistory:
    def test_formats_messages(self):
        r = CognitiveRefiner()
        history = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = r._format_history(history)
        assert "[USER]" in result
        assert "[ASSISTANT]" in result
        assert "hello" in result

    def test_empty(self):
        r = CognitiveRefiner()
        assert r._format_history([]) == ""


class TestRefineContext:
    def test_empty_history(self):
        r = CognitiveRefiner()
        result = r.refine_context([])
        assert result["refined_content"] == ""
        assert result["metadata"]["refined"] is False
        assert result["metadata"]["reason"] == "empty_history"

    def test_below_threshold_no_refinement(self):
        r = CognitiveRefiner()
        history = [{"content": "short message", "role": "user"}]
        result = r.refine_context(history, max_tokens=8000)
        assert result["metadata"]["refined"] is False
        assert result["metadata"]["reason"] == "below_threshold"

    @patch("aura_cli.core.memory.cognitive_refiner.query_with_fallback")
    def test_above_threshold_calls_llm(self, mock_query):
        mock_query.return_value = MagicMock(
            choices=[
                MagicMock(
                    message=MagicMock(
                        content=json.dumps(
                            {
                                "refined_content": "refined",
                                "summary": "summary",
                                "key_points": ["p1"],
                                "important_decisions": [],
                                "file_references": [],
                            }
                        )
                    )
                )
            ]
        )
        r = CognitiveRefiner()
        # Large history to exceed threshold
        history = [{"content": "x" * 10000, "role": "user"}]
        result = r.refine_context(history, max_tokens=1000)
        assert result["metadata"]["refined"] is True
        mock_query.assert_called_once()

    @patch(
        "aura_cli.core.memory.cognitive_refiner.query_with_fallback",
        side_effect=Exception("err"),
    )
    def test_llm_failure_uses_fallback(self, mock_query):
        r = CognitiveRefiner()
        history = [{"content": "x" * 10000, "role": "user"}]
        result = r.refine_context(history, max_tokens=1000)
        assert result["metadata"]["refined"] is True
        assert result["metadata"]["mode"] == "fallback"


class TestRefineFallback:
    def test_preserves_system_messages(self):
        r = CognitiveRefiner()
        history = [
            {"role": "system", "content": "system prompt"},
            {"role": "user", "content": "casual chat"},
        ]
        result = r._refine_fallback(history)
        assert "system prompt" in result["refined_content"]

    def test_preserves_file_references(self):
        r = CognitiveRefiner()
        history = [
            {"role": "user", "content": "Edit the file main.py and utils.js"},
        ]
        result = r._refine_fallback(history)
        assert "main.py" in result["refined_content"]

    def test_preserves_decision_keywords(self):
        r = CognitiveRefiner()
        history = [
            {"role": "user", "content": "Vamos implementar usando FastAPI"},
        ]
        result = r._refine_fallback(history)
        assert "FastAPI" in result["refined_content"]

    def test_preserves_recent_messages(self):
        r = CognitiveRefiner()
        history = [{"role": "user", "content": f"msg {i}"} for i in range(20)]
        result = r._refine_fallback(history)
        # Last 10 should be preserved
        assert "msg 19" in result["refined_content"]

    def test_metadata(self):
        r = CognitiveRefiner()
        history = [{"role": "user", "content": "hello"}]
        result = r._refine_fallback(history)
        assert result["metadata"]["refined"] is True
        assert result["metadata"]["mode"] == "fallback"
        assert result["metadata"]["original_messages"] == 1


class TestExtractJsonFromText:
    def test_valid_json(self):
        r = CognitiveRefiner()
        text = 'some text {"summary": "hello", "key_points": []} more text'
        result = r._extract_json_from_text(text)
        assert result.get("summary") == "hello"

    def test_no_json(self):
        r = CognitiveRefiner()
        result = r._extract_json_from_text("no json here at all")
        assert "refined_content" in result
        assert result["metadata"]["mode"] == "fallback"

    def test_long_text_truncated(self):
        r = CognitiveRefiner()
        result = r._extract_json_from_text("x" * 10000)
        assert len(result["refined_content"]) <= 5000


class TestGetCognitiveRefiner:
    def test_returns_instance(self):
        # Reset singleton
        if hasattr(get_cognitive_refiner, "_instance"):
            del get_cognitive_refiner._instance
        r = get_cognitive_refiner()
        assert isinstance(r, CognitiveRefiner)

    def test_returns_same_instance(self):
        if hasattr(get_cognitive_refiner, "_instance"):
            del get_cognitive_refiner._instance
        r1 = get_cognitive_refiner()
        r2 = get_cognitive_refiner()
        assert r1 is r2
        # Cleanup
        del get_cognitive_refiner._instance
