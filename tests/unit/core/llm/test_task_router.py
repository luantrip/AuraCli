"""Tests for the intelligent task router."""

import os
from unittest.mock import patch

from aura_cli.core.llm.model_utils import (
    DEFAULT_MODEL,
    get_model_catalog,
    normalize_provider_name,
)
from aura_cli.core.llm.task_router import (
    MODEL_PROFILES,
    TaskRouter,
    TaskType,
    get_task_router,
)


class TestTaskTypeDetection:
    def test_detects_code_edit(self):
        router = TaskRouter()
        assert router.detect_task_type("Crie um arquivo main.py") == TaskType.CODE_EDIT
        assert router.detect_task_type("Create a new class") == TaskType.CODE_EDIT

    def test_detects_shell_command(self):
        router = TaskRouter()
        assert router.detect_task_type("ls -la") == TaskType.SHELL_COMMAND
        assert router.detect_task_type("Execute npm install") == TaskType.SHELL_COMMAND

    def test_detects_git_operation(self):
        router = TaskRouter()
        assert router.detect_task_type("push to origin") == TaskType.GIT_OPERATION
        assert router.detect_task_type("Faca um commit") == TaskType.GIT_OPERATION

    def test_detects_architecture(self):
        router = TaskRouter()
        assert (
            router.detect_task_type("Refatore a arquitetura do projeto")
            == TaskType.ARCHITECTURE
        )

    def test_detects_test_generation(self):
        router = TaskRouter()
        assert (
            router.detect_task_type("Gere testes para o modulo")
            == TaskType.TEST_GENERATION
        )

    def test_detects_debug(self):
        router = TaskRouter()
        assert router.detect_task_type("Fix o bug no parser") == TaskType.DEBUG

    def test_defaults_to_quick_question(self):
        router = TaskRouter()
        assert router.detect_task_type("Hello") == TaskType.QUICK_QUESTION


class TestRouting:
    def test_routes_to_available_model(self):
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=True):
            router = TaskRouter()
            router.reset()
            model = router.route("Crie um arquivo")
            assert "gemini" in model

    def test_fallback_when_no_keys(self):
        with patch.dict(os.environ, {}, clear=True):
            router = TaskRouter()
            router.reset()
            model = router.route("anything")
            # Should return DEFAULT_MODEL
            assert model is not None

    def test_prefers_free_models(self):
        with patch.dict(
            os.environ,
            {"GEMINI_API_KEY": "k", "OPENAI_API_KEY": "k"},
            clear=True,
        ):
            router = TaskRouter(prefer_free=True)
            router.reset()
            model = router.route("Crie um arquivo")
            assert "gemini" in model  # gemini is free, openai is expensive

    def test_singleton(self):
        r1 = get_task_router()
        r2 = get_task_router()
        assert r1 is r2

    def test_profiles_use_ids_from_canonical_catalog(self):
        catalog = get_model_catalog()

        for profile in MODEL_PROFILES:
            provider = normalize_provider_name(profile.provider)
            assert (
                profile.model_id in catalog.get(provider, [])
                or profile.model_id == DEFAULT_MODEL
            )
