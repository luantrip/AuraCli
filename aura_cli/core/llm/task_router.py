"""Intelligent task-based model router.

Routes tasks to the most appropriate model based on task type,
available API keys, and model capabilities.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
import os
import re
from typing import TYPE_CHECKING, Dict, List, Optional

from aura_cli.core.llm.model_utils import (
    DEFAULT_MODEL,
    get_models_for_provider,
    normalize_model_name,
)

if TYPE_CHECKING:
    from aura_cli.core.llm.model_profiles import ModelProfileManager

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Categories of development tasks."""

    CODE_EDIT = "code_edit"  # Writing/modifying code
    CODE_REVIEW = "code_review"  # Analyzing existing code
    SHELL_COMMAND = "shell_command"  # Terminal operations
    ARCHITECTURE = "architecture"  # System design and planning
    QUICK_QUESTION = "quick_question"  # Simple Q&A
    FILE_OPERATION = "file_operation"  # Read/write/search files
    GIT_OPERATION = "git_operation"  # Version control
    TEST_GENERATION = "test_gen"  # Writing tests
    DOCUMENTATION = "documentation"  # Writing docs
    DEBUG = "debug"  # Debugging issues


@dataclass
class ModelProfile:
    """Model capabilities profile."""

    model_id: str
    provider: str
    strengths: List[TaskType]
    speed: str  # "fast", "medium", "slow"
    cost: str  # "free", "cheap", "expensive"
    env_key: str  # Required env var


def _catalog_model(provider: str, index: int, fallback: str) -> str:
    """Read a model ID from the canonical catalog with a safe fallback."""
    models = get_models_for_provider(provider)
    return models[index] if len(models) > index else fallback


# Model profiles ordered by preference within each task type. Task metadata stays
# here; provider/model identity comes from the canonical catalog.
MODEL_PROFILES: List[ModelProfile] = [
    ModelProfile(
        _catalog_model("groq", 0, "groq/openai/gpt-oss-20b"),
        "groq",
        [
            TaskType.CODE_EDIT,
            TaskType.QUICK_QUESTION,
            TaskType.FILE_OPERATION,
            TaskType.SHELL_COMMAND,
            TaskType.GIT_OPERATION,
            TaskType.DOCUMENTATION,
        ],
        speed="fast",
        cost="free",
        env_key="GROQ_API_KEY",
    ),
    ModelProfile(
        _catalog_model("groq", 1, "groq/openai/gpt-oss-120b"),
        "groq",
        [
            TaskType.CODE_REVIEW,
            TaskType.ARCHITECTURE,
            TaskType.DEBUG,
            TaskType.TEST_GENERATION,
            TaskType.CODE_EDIT,
        ],
        speed="fast",
        cost="free",
        env_key="GROQ_API_KEY",
    ),
    ModelProfile(
        _catalog_model("cerebras", 0, "cerebras/gpt-oss-120b"),
        "cerebras",
        [
            TaskType.CODE_EDIT,
            TaskType.QUICK_QUESTION,
            TaskType.FILE_OPERATION,
            TaskType.SHELL_COMMAND,
            TaskType.GIT_OPERATION,
            TaskType.DOCUMENTATION,
            TaskType.DEBUG,
            TaskType.TEST_GENERATION,
        ],
        speed="fast",
        cost="free",
        env_key="CEREBRAS_API_KEY",
    ),
    ModelProfile(
        _catalog_model("cerebras", 1, "cerebras/gpt-oss-120b"),
        "cerebras",
        [
            TaskType.ARCHITECTURE,
            TaskType.CODE_REVIEW,
            TaskType.DEBUG,
            TaskType.TEST_GENERATION,
            TaskType.CODE_EDIT,
        ],
        speed="fast",
        cost="free",
        env_key="CEREBRAS_API_KEY",
    ),
    ModelProfile(
        _catalog_model("gemini", 0, "gemini/gemini-2.5-flash"),
        "gemini",
        [
            TaskType.CODE_EDIT,
            TaskType.QUICK_QUESTION,
            TaskType.FILE_OPERATION,
            TaskType.SHELL_COMMAND,
            TaskType.GIT_OPERATION,
            TaskType.DOCUMENTATION,
        ],
        speed="fast",
        cost="free",
        env_key="GEMINI_API_KEY",
    ),
    ModelProfile(
        _catalog_model("gemini", 1, "gemini/gemini-2.5-pro"),
        "gemini",
        [
            TaskType.ARCHITECTURE,
            TaskType.CODE_REVIEW,
            TaskType.DEBUG,
            TaskType.TEST_GENERATION,
        ],
        speed="medium",
        cost="free",
        env_key="GEMINI_API_KEY",
    ),
    ModelProfile(
        _catalog_model(
            "openrouter",
            0,
            "openrouter/free",
        ),
        "openrouter",
        [
            TaskType.CODE_EDIT,
            TaskType.CODE_REVIEW,
            TaskType.DEBUG,
            TaskType.ARCHITECTURE,
            TaskType.TEST_GENERATION,
        ],
        speed="fast",
        cost="free",
        env_key="OPENROUTER_API_KEY",
    ),
    ModelProfile(
        _catalog_model(
            "openrouter",
            2,
            "openrouter/nvidia/nemotron-3-ultra-550b-a55b:free",
        ),
        "openrouter",
        [TaskType.QUICK_QUESTION, TaskType.FILE_OPERATION, TaskType.DOCUMENTATION],
        speed="fast",
        cost="free",
        env_key="OPENROUTER_API_KEY",
    ),
    ModelProfile(
        _catalog_model(
            "openrouter",
            4,
            "openrouter/cohere/north-mini-code:free",
        ),
        "openrouter",
        [TaskType.CODE_EDIT, TaskType.DEBUG, TaskType.QUICK_QUESTION],
        speed="fast",
        cost="free",
        env_key="OPENROUTER_API_KEY",
    ),
    ModelProfile(
        _catalog_model("gpt", 0, "gpt-4o"),
        "openai",
        [
            TaskType.ARCHITECTURE,
            TaskType.CODE_REVIEW,
            TaskType.DEBUG,
            TaskType.CODE_EDIT,
            TaskType.TEST_GENERATION,
        ],
        speed="medium",
        cost="expensive",
        env_key="OPENAI_API_KEY",
    ),
    ModelProfile(
        _catalog_model("claude", 0, "claude-sonnet-4-6"),
        "anthropic",
        [
            TaskType.CODE_EDIT,
            TaskType.CODE_REVIEW,
            TaskType.ARCHITECTURE,
            TaskType.DEBUG,
            TaskType.DOCUMENTATION,
        ],
        speed="medium",
        cost="expensive",
        env_key="ANTHROPIC_API_KEY",
    ),
]

# Patterns for task detection
_TASK_PATTERNS: Dict[TaskType, List[str]] = {
    TaskType.SHELL_COMMAND: [
        r"^(run|execute|roda|execut)",
        r"(comando|command|terminal|shell)",
        r"^(ls|cd|mkdir|rm|cat|grep|find|ps|docker|npm|pip|git)\b",
    ],
    TaskType.GIT_OPERATION: [
        r"(git|commit|push|pull|branch|merge|rebase|stash|diff|log)",
    ],
    TaskType.CODE_EDIT: [
        r"(cri[ae]|create|escrev|write|modifi|edit|alter|change|add|implement|refactor)",
        r"(arquivo|file|classe|class|funcao|function|metodo|method)",
    ],
    TaskType.CODE_REVIEW: [
        r"(revis|review|analise? o codigo|analyze.*code|check.*code)",
        r"(bug|problema|issue|erro|error).*codigo",
    ],
    TaskType.ARCHITECTURE: [
        r"(arquitetura|architecture|design|plano|plan|estrutur|structure)",
        r"(refator|refactor).*projeto",
        r"(como.*(organiz|structur)|how.*(organiz|structur))",
    ],
    TaskType.TEST_GENERATION: [
        r"(test|teste|spec|tdd)",
        r"(gere?|generate|crie?|create).*(test|teste)",
    ],
    TaskType.DOCUMENTATION: [
        r"(doc|documenta|readme|changelog|comment)",
        r"(expli[cq]|explain)",
    ],
    TaskType.DEBUG: [
        r"(debug|depura|por ?que.*(falh|err|quebr)|why.*(fail|err|break))",
        r"(fix|corrij|consert|repair)",
    ],
    TaskType.FILE_OPERATION: [
        r"(leia|read|abr[ae]|open|list|mostr|show).*(arquivo|file|diretorio|director)",
        r"(tree|arvore|estrutura de pastas)",
    ],
    TaskType.QUICK_QUESTION: [
        r"^(o que|what|como|how|qual|which|quando|when|por ?que|why)",
        r"(explique|explain|me (fale|diga|conte)|tell me)",
    ],
}


class TaskRouter:
    """Routes tasks to optimal models based on task type and availability.

    This is the SINGLE entry point for model selection in Aura CLI.
    The selection hierarchy is:

    1. User preferences (via ModelProfileManager) — if the user has set a
       preferred model for this task type, honour it.
    2. Task-type → model mapping with availability/cost/speed scoring
       (the built-in MODEL_PROFILES table).
    3. Fallback to DEFAULT_MODEL when nothing else is available.

    Note: Retry/fallback across providers when a model *fails* is handled
    separately by ``multi_model.py`` (MultiModelIntelligence). That module
    does NOT perform initial model selection.
    """

    def __init__(self, prefer_free: bool = True):
        self.prefer_free = prefer_free
        self._available_profiles: Optional[List[ModelProfile]] = None
        self._profile_manager: Optional[ModelProfileManager] = None

    @property
    def profile_manager(self):
        """Lazy-loaded ModelProfileManager sub-component."""
        if self._profile_manager is None:
            try:
                from aura_cli.core.llm.model_profiles import get_profile_manager

                self._profile_manager = get_profile_manager()
            except Exception as _e:
                logger.debug("ModelProfileManager unavailable, routing without profiles: %s", _e)
        return self._profile_manager

    def _get_available_profiles(self) -> List[ModelProfile]:
        """Get profiles for models that have configured API keys."""
        if self._available_profiles is not None:
            return self._available_profiles

        available = []
        for profile in MODEL_PROFILES:
            if os.environ.get(profile.env_key):
                available.append(profile)

        self._available_profiles = available
        return available

    def detect_task_type(self, user_input: str) -> TaskType:
        """Detect the task type from user input."""
        input_lower = user_input.lower().strip()

        scores: Dict[TaskType, int] = dict.fromkeys(TaskType, 0)

        for task_type, patterns in _TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, input_lower):
                    scores[task_type] += 1

        # Return highest scoring, or QUICK_QUESTION as default
        best = max(scores, key=lambda task_type: scores[task_type])
        if scores[best] == 0:
            return TaskType.QUICK_QUESTION
        return best

    def route(self, user_input: str) -> str:
        """Compatibility alias for the canonical :meth:`select_model` path."""
        return self.select_model(user_input)

    def select_model(
        self, query: str, available_models: Optional[List[str]] = None
    ) -> str:
        """Single entry point for model selection across the entire application.

        Selection hierarchy:
            1. Check ModelProfileManager for a user-preferred model for the
               detected task type.
            2. Fall back to the task-type → model mapping (MODEL_PROFILES table)
               filtered by available API keys and cost/speed preference.
            3. Ultimate fallback to DEFAULT_MODEL.

        Args:
            query: The user's natural-language query/command.
            available_models: Optional explicit list of models to consider.
                              If provided, the selected model must be in this list
                              or we fall back through the hierarchy.

        Returns:
            Model identifier string (e.g. "gemini/gemini-2.5-flash").
        """
        task_type = self.detect_task_type(query)
        available_models = (
            [normalize_model_name(model) or model for model in available_models]
            if available_models
            else None
        )

        # --- Step 1: Check user preference via ModelProfileManager ---
        preferred = self._get_user_preferred_model(task_type)
        if preferred and (available_models is None or preferred in available_models):
            logger.debug(
                f"TaskRouter.select_model: user preference "
                f"'{preferred}' for {task_type.value}"
            )
            return preferred

        # --- Step 2: Task-type → model mapping with availability ---
        model = self._select_from_profiles(task_type, available_models)
        if model:
            logger.debug(
                f"TaskRouter.select_model: profile match "
                f"'{model}' for {task_type.value}"
            )
            return model

        # --- Step 3: Ultimate fallback ---
        logger.debug("TaskRouter.select_model: falling back to DEFAULT_MODEL")
        return DEFAULT_MODEL

    def _get_user_preferred_model(self, task_type: TaskType) -> Optional[str]:
        """Query ModelProfileManager for user's preferred model for this task type."""
        mgr = self.profile_manager
        if mgr is None:
            return None
        try:
            return mgr.get_preferred_model(task_type.value)
        except Exception:
            return None

    def _select_from_profiles(
        self, task_type: TaskType, available_models: Optional[List[str]] = None
    ) -> Optional[str]:
        """Select best model from MODEL_PROFILES for a given task type."""
        available = self._get_available_profiles()

        if not available:
            return None

        # Filter by task type strength
        candidates = [p for p in available if task_type in p.strengths]
        if not candidates:
            candidates = available

        # If caller constrains to a set of models, filter further
        if available_models:
            constrained = [p for p in candidates if p.model_id in available_models]
            if constrained:
                candidates = constrained

        # Sort: free first (if preferred), then by speed
        speed_order = {"fast": 0, "medium": 1, "slow": 2}
        cost_order = {"free": 0, "cheap": 1, "expensive": 2}

        def sort_key(p: ModelProfile):
            cost = cost_order.get(p.cost, 9) if self.prefer_free else 0
            speed = speed_order.get(p.speed, 9)
            return (cost, speed)

        candidates.sort(key=sort_key)
        return candidates[0].model_id if candidates else None

    def reset(self):
        """Reset cached availability (call after key changes)."""
        self._available_profiles = None


def get_task_router() -> TaskRouter:
    """Get the global task router instance via DI container."""
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.TASK_ROUTER):
            return container.resolve(Services.TASK_ROUTER)
    except Exception:
        pass
    # Simple fallback (no globals needed — container handles thread safety)
    return TaskRouter()
