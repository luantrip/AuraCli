"""Model profile manager — routes tasks to optimal LLM models.

Profiles (advanced_reasoning, advanced_coding, intermediate_reasoning,
quick_reasoning, intent_router, low_cost_search) are stored in
~/.aura/model_profiles.json with built-in defaults. Integrates with
process_function_calls_loop for automatic task-complexity routing.
"""

from copy import deepcopy
import json
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional

from aura_cli.core.llm.model_utils import (
    DEFAULT_GEMINI_MODEL,
    DEFAULT_MODEL,
    normalize_model_name,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class ModelProfileManager:
    """
    Manages model profiles for different task types.

    The manager maintains a mapping of task profiles to specific LLM models,
    allowing intelligent model selection based on task complexity and requirements.

    Attributes:
        config_path: Path to the configuration file
        profiles: Dictionary containing profile configurations
    """

    DEFAULT_PROFILES: ClassVar[Dict[str, Any]] = {
        "profiles": {},
        "default_profile": "advanced_coding",
        "task_routing": {
            "patterns": {
                "advanced_reasoning": [
                    "architect",
                    "design",
                    "plan",
                    "strategy",
                    "complex",
                    "refactor",
                ],
                "advanced_coding": [
                    "implement",
                    "create",
                    "build",
                    "write code",
                    "function",
                    "class",
                ],
                "intermediate_reasoning": [
                    "review",
                    "validate",
                    "check",
                    "summarize",
                    "explain",
                ],
                "quick_reasoning": [
                    "fix",
                    "format",
                    "typo",
                    "simple",
                    "quick",
                    "rename",
                ],
                "low_cost_search": [
                    "find",
                    "search",
                    "locate",
                    "list",
                    "where",
                ],
            }
        },
    }

    _instance: Optional["ModelProfileManager"] = None

    def __new__(cls, *args, **kwargs):
        """Enforce singleton pattern for the model profile manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize the model profile manager.

        Args:
            config_path: Optional custom path for configuration file.
                        Default: ~/.aura/model_profiles.json
        """
        if hasattr(self, "_initialized") and self._initialized:  # type: ignore[has-type]
            return

        self.config_path = config_path or self._get_default_config_path()
        self.profiles = self._load_profiles()
        self._initialized = True

        logger.info(f"ModelProfileManager initialized: {self.config_path}")

    def _get_default_config_path(self) -> Path:
        """Return the default configuration file path."""
        from aura_cli.core.paths import get_aura_home

        config_dir = get_aura_home()
        config_dir.mkdir(exist_ok=True)
        return config_dir / "model_profiles.json"

    def _load_profiles(self) -> Dict[str, Any]:
        """
        Load profiles from configuration file or use defaults.

        Returns:
            Dictionary containing profile configuration
        """
        if self.config_path.exists():
            try:
                with open(self.config_path, encoding="utf-8") as f:
                    profiles = json.load(f)

                if "profiles" in profiles and "default_profile" in profiles:
                    logger.info(f"Profiles loaded from {self.config_path}")
                    return profiles

            except json.JSONDecodeError as e:
                logger.warning(f"Error decoding profiles JSON: {e}")
            except Exception as e:
                logger.warning(f"Error loading profiles: {e}")

        default_profiles = self._build_default_profiles()
        self._save_profiles(default_profiles)
        return default_profiles

    @classmethod
    def _build_default_profiles(cls) -> Dict[str, Any]:
        """Build runtime defaults from the centralized model catalog."""
        profiles = deepcopy(cls.DEFAULT_PROFILES)
        profiles["profiles"] = {
            "advanced_reasoning": DEFAULT_MODEL,
            "advanced_coding": DEFAULT_MODEL,
            "intermediate_reasoning": DEFAULT_GEMINI_MODEL,
            "quick_reasoning": DEFAULT_GEMINI_MODEL,
            "intent_router": DEFAULT_GEMINI_MODEL,
            "low_cost_search": DEFAULT_GEMINI_MODEL,
        }
        return profiles

    def _save_profiles(self, profiles: Dict[str, Any]) -> None:
        """
        Save profiles to configuration file.

        Args:
            profiles: Profile configuration to save
        """
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(profiles, f, indent=2, ensure_ascii=False)
            logger.info(f"Perfis salvos em {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving profiles: {e}")

    def get_model(self, profile_type: str) -> str:
        """
        Get the model configured for a specific profile type.

        Args:
            profile_type: Type of profile (advanced_reasoning, quick_reasoning, etc.)

        Returns:
            Model name configured for the profile (e.g., "gemini/gemini-2.5-pro")
        """
        profiles = self.profiles.get("profiles", {})

        if profile_type in profiles:
            model = normalize_model_name(profiles[profile_type]) or DEFAULT_MODEL
            logger.debug(f"Modelo para '{profile_type}': {model}")
            return model

        default = self.profiles.get("default_profile", "advanced_coding")
        logger.warning(f"Perfil '{profile_type}' not found, using '{default}'")
        return normalize_model_name(profiles.get(default)) or DEFAULT_MODEL

    def update_profile(self, profile_type: str, model_name: str) -> bool:
        """
        Update a profile with a new model.

        Args:
            profile_type: Profile type to update
            model_name: New model name

        Returns:
            True if successful, False otherwise
        """
        profiles = self.profiles.get("profiles", {})

        if profile_type not in profiles:
            logger.error(f"Perfil '{profile_type}' não existe")
            return False

        canonical_model = normalize_model_name(model_name) or DEFAULT_MODEL
        profiles[profile_type] = canonical_model
        self.profiles["profiles"] = profiles
        self._save_profiles(self.profiles)
        logger.info(f"Perfil '{profile_type}' atualizado para '{canonical_model}'")
        return True

    def add_profile(self, profile_type: str, model_name: str) -> bool:
        """
        Add a new profile.

        Args:
            profile_type: New profile type name
            model_name: Model to use for this profile

        Returns:
            True if successful, False if profile already exists
        """
        profiles = self.profiles.get("profiles", {})

        if profile_type in profiles:
            logger.warning(f"Perfil '{profile_type}' já existe, use update_profile()")
            return False

        canonical_model = normalize_model_name(model_name) or DEFAULT_MODEL
        profiles[profile_type] = canonical_model
        self.profiles["profiles"] = profiles
        self._save_profiles(self.profiles)
        logger.info(
            f"Perfil '{profile_type}' adicionado com modelo '{canonical_model}'"
        )
        return True

    def list_profiles(self) -> Dict[str, str]:
        """
        List all available profiles.

        Returns:
            Dictionary mapping profile types to model names
        """
        return {
            profile: normalize_model_name(model) or DEFAULT_MODEL
            for profile, model in self.profiles.get("profiles", {}).items()
        }

    def get_default_profile(self) -> str:
        """
        Get the default profile type.

        Returns:
            Default profile type name
        """
        return self.profiles.get("default_profile", "advanced_coding")

    def set_default_profile(self, profile_type: str) -> bool:
        """
        Set the default profile type.

        Args:
            profile_type: Profile type to set as default

        Returns:
            True if successful, False if profile doesn't exist
        """
        if profile_type not in self.profiles.get("profiles", {}):
            logger.error(f"Perfil '{profile_type}' não existe")
            return False

        self.profiles["default_profile"] = profile_type
        self._save_profiles(self.profiles)
        logger.info(f"Perfil padrão definido como '{profile_type}'")
        return True

    def detect_task_type(self, prompt: str) -> str:
        """
        Automatically detect the task type from a user prompt.

        Uses keyword matching to determine the appropriate profile type
        for a given task description.

        Args:
            prompt: User prompt or task description

        Returns:
            Detected profile type (e.g., "advanced_coding", "quick_reasoning")
        """
        prompt_lower = prompt.lower()
        routing = self.profiles.get("task_routing", {}).get("patterns", {})

        scores: Dict[str, int] = {}

        for profile_type, keywords in routing.items():
            score = sum(1 for keyword in keywords if keyword in prompt_lower)
            if score > 0:
                scores[profile_type] = score

        if scores:
            best_match = max(scores, key=scores.get)  # type: ignore
            logger.debug(
                f"Tipo de tarefa detectado: {best_match} (score: {scores[best_match]})"
            )
            return best_match

        default = self.get_default_profile()
        logger.debug(f"Nenhum padrão detectado, usando perfil padrão: {default}")
        return default

    def get_model_for_task(self, prompt: str) -> str:
        """
        Get the appropriate model for a task based on automatic detection.

        Convenience wrapper around ``detect_task_type()`` + ``get_model()``.
        Prefer ``TaskRouter.select_model()`` for new code — it applies the full
        selection hierarchy (user preferences → profiles → fallback).

        Args:
            prompt: User prompt or task description

        Returns:
            Model name appropriate for the detected task type
        """
        task_type = self.detect_task_type(prompt)
        return self.get_model(task_type)

    def get_preferred_model(self, task_type: str) -> Optional[str]:
        """
        Get the user's preferred model for a specific task type, if one exists.

        This is used by TaskRouter as step 1 of the model selection hierarchy.
        It maps TaskRouter's TaskType values (e.g. "code_edit") to profile
        categories (e.g. "advanced_coding") and returns the configured model.

        Args:
            task_type: TaskType enum value string (e.g. "code_edit", "architecture")

        Returns:
            Model name if a user preference exists, None otherwise
        """
        # Map TaskRouter task types to ModelProfileManager profile categories
        _TASK_TO_PROFILE: Dict[str, str] = {
            "code_edit": "advanced_coding",
            "code_review": "intermediate_reasoning",
            "shell_command": "quick_reasoning",
            "architecture": "advanced_reasoning",
            "quick_question": "quick_reasoning",
            "file_operation": "low_cost_search",
            "git_operation": "quick_reasoning",
            "test_gen": "advanced_coding",
            "documentation": "intermediate_reasoning",
            "debug": "advanced_reasoning",
        }

        profile_key = _TASK_TO_PROFILE.get(task_type)
        if not profile_key:
            return None

        profiles = self.profiles.get("profiles", {})
        model = normalize_model_name(profiles.get(profile_key))

        if not model:
            return None

        # Only return as a "preference" if the user has customized it
        # (i.e. it differs from the built-in defaults)
        defaults = self._build_default_profiles().get("profiles", {})
        if model == defaults.get(profile_key):
            # Not customized — let TaskRouter use its own logic
            return None

        return model

    def get_all_models(self) -> List[str]:
        """
        Get list of all unique models configured across all profiles.

        Returns:
            List of unique model names
        """
        models = {
            normalize_model_name(model) or DEFAULT_MODEL
            for model in self.profiles.get("profiles", {}).values()
        }
        return sorted(models)

    def reset_to_defaults(self) -> None:
        """Reset all profiles to default configuration."""
        self.profiles = self._build_default_profiles()
        self._save_profiles(self.profiles)
        logger.info("Perfis resetados para valores padrão")


_profile_manager: Optional[ModelProfileManager] = None


def get_profile_manager() -> ModelProfileManager:
    """
    Get the global ModelProfileManager instance.

    Returns:
        Singleton ModelProfileManager instance
    """
    global _profile_manager
    if _profile_manager is None:
        _profile_manager = ModelProfileManager()
    return _profile_manager


def reset_profile_manager() -> None:
    """Reset the global ModelProfileManager instance."""
    global _profile_manager
    _profile_manager = None
