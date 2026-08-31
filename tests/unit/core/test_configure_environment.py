"""Testes para AgiExecutionEngine._configure_environment() — TEST-NEW-05."""

from unittest.mock import MagicMock

from aura_cli.core.agi.execution import AgiExecutionEngine


def _make_engine(model="gemini/gemini-2.5-flash", api_keys=None):
    worker = MagicMock()
    worker.model = model
    worker.api_keys = api_keys or {}
    worker.available_tools = {}
    worker.headless = True
    worker.task_id = "task-1"
    worker.result_queue = MagicMock()
    worker.use_advanced_features = False
    worker.agi_event_adapter = MagicMock()
    return AgiExecutionEngine(
        agi_worker=worker,
        planner=None,
        context_manager=None,
        validator=None,
        workflow_executor=None,
        orchestrator=None,
        git_manager=None,
    )


class TestConfigureEnvironment:
    def test_gemini_with_key_returns_key_and_model(self):
        engine = _make_engine(
            model="gemini/gemini-2.5-flash",
            api_keys={"GOOGLE_API_KEY": "gk-test"},
        )
        key, model = engine._configure_environment()
        assert key == "gk-test"
        assert model is not None

    def test_gemini_missing_key_returns_none(self):
        engine = _make_engine(model="gemini/gemini-2.5-flash", api_keys={})
        key, _model = engine._configure_environment()
        assert key is None

    def test_claude_with_key_returns_key(self):
        engine = _make_engine(
            model="claude-3-5-sonnet",
            api_keys={"ANTHROPIC_API_KEY": "ak-test"},
        )
        key, _model = engine._configure_environment()
        assert key == "ak-test"

    def test_claude_missing_key_returns_none(self):
        engine = _make_engine(model="claude-3-5-sonnet", api_keys={})
        key, _model = engine._configure_environment()
        assert key is None

    def test_gpt_with_key_returns_key(self):
        engine = _make_engine(
            model="gpt-4o",
            api_keys={"OPENAI_API_KEY": "ok-test"},
        )
        key, _model = engine._configure_environment()
        assert key == "ok-test"

    def test_gpt_missing_key_returns_none(self):
        engine = _make_engine(model="gpt-4o", api_keys={})
        key, _model = engine._configure_environment()
        assert key is None

    def test_openrouter_with_key_returns_key(self):
        engine = _make_engine(
            model="openrouter/meta-llama/llama-3.3-70b",
            api_keys={"OPENROUTER_API_KEY": "or-test"},
        )
        key, _model = engine._configure_environment()
        assert key == "or-test"

    def test_nvidia_with_key_returns_key(self):
        engine = _make_engine(
            model="openai/nvidia/llama-3.3-nemotron-super-49b-v1",
            api_keys={"NVIDIA_API_KEY": "nv-test"},
        )
        key, _model = engine._configure_environment()
        assert key == "nv-test"

    def test_unknown_provider_falls_back_to_google(self):
        engine = _make_engine(
            model="unknown-model",
            api_keys={"GOOGLE_API_KEY": "gk-fallback"},
        )
        key, _model = engine._configure_environment()
        assert key == "gk-fallback"

    def test_unknown_provider_no_key_returns_none(self):
        engine = _make_engine(model="unknown-model", api_keys={})
        key, _model = engine._configure_environment()
        assert key is None
