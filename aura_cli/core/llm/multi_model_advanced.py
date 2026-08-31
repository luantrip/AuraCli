"""Advanced multi-model intelligence with response cache and preference learning.

STATUS (2026-08): ACTIVE — two runtime callers (both in try/except, non-critical):
  1. llm_handler.py → ModelPreferenceLearner().record_decision()
  2. function_call_handler.py → AdvancedMultiModelIntelligence(enable_learning=True)

Extends multi_model.py with ModelPreferenceLearner (per-task model scoring),
ResponseCache (deduplication), and smart_query_with_learning().
"""

from collections import OrderedDict, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from aura_cli.core.llm.model_utils import normalize_model_name
from aura_cli.core.llm.multi_model import MultiModelIntelligence
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class ModelPreferenceLearner:
    """Learns user model preferences for smarter selection."""

    def __init__(self, cache_dir: Optional[str] = None):
        """
        Initialise the preference learner

        Args:
            cache_dir: Cache directory.
        """
        from aura_cli.core.paths import aura_path

        self.cache_dir = (
            Path(cache_dir) if cache_dir else aura_path("model_preferences")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.decision_history: List[Dict[str, Any]] = []
        self.model_scores: Dict[str, float] = defaultdict(float)
        self.task_type_preferences: Dict[str, Dict[str, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        self._preferences_file = self.cache_dir / "preferences.json"
        self._load_preferences()

    def record_decision(
        self,
        task_type: str,
        models_used: List[str],
        selected_model: str,
        user_feedback: Optional[str] = None,
    ):
        """Record a model selection decision for learning."""
        canonical_models = [
            canonical
            for model in models_used
            if (canonical := normalize_model_name(model))
        ]
        canonical_selected = normalize_model_name(selected_model) or selected_model
        decision = {
            "task_type": task_type,
            "models_used": canonical_models,
            "selected_model": canonical_selected,
            "user_feedback": user_feedback,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

        self.decision_history.append(decision)
        self.decision_history = self.decision_history[-500:]

        if user_feedback:
            score_delta = {
                "excellent": 2.0,
                "good": 1.0,
                "bad": -1.0,
                "poor": -2.0,
            }.get(user_feedback.lower(), 0.0)

            self.model_scores[canonical_selected] += score_delta
            self.task_type_preferences[task_type][canonical_selected] += score_delta

        self._save_preferences()

    def record_outcome(self, task_type: str, model: str, *, supported: bool) -> None:
        """Learn from a verified task outcome, never from response production alone."""
        feedback = "good" if supported else "bad"
        self.record_decision(task_type, [model], model, user_feedback=feedback)

    def get_best_model_for_task(
        self, task_type: str, available_models: List[str]
    ) -> Optional[str]:
        """Return the best model for a task type based on history."""
        if task_type not in self.task_type_preferences:
            return None

        preferences = self.task_type_preferences[task_type]
        canonical_available = {
            canonical
            for model in available_models
            if (canonical := normalize_model_name(model))
        }

        available_preferences = {
            model: score
            for model, score in preferences.items()
            if model in canonical_available
        }

        if not available_preferences:
            return None

        best_model = max(available_preferences.items(), key=lambda x: x[1])[0]
        return best_model

    def get_model_ranking(
        self, task_type: Optional[str] = None
    ) -> List[Tuple[str, float]]:
        """Return models ranked by performance score."""
        if task_type:
            preferences = self.task_type_preferences.get(task_type, {})
        else:
            preferences = self.model_scores

        ranking = sorted(preferences.items(), key=lambda x: x[1], reverse=True)
        return ranking

    def _save_preferences(self):
        """Persist preferences to cache."""
        try:
            cache_data = {
                "decision_history": self.decision_history[-1000:],
                "model_scores": dict(self.model_scores),
                "task_type_preferences": {
                    k: dict(v) for k, v in self.task_type_preferences.items()
                },
                "timestamp": datetime.now(tz=timezone.utc).isoformat(),
            }

            with open(self._preferences_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Error saving preferences: {e}")

    def _load_preferences(self):
        """Load preferences from cache."""
        if not self._preferences_file.exists():
            return

        try:
            with open(self._preferences_file, encoding="utf-8") as f:
                cache_data = json.load(f)

            self.decision_history = [
                {
                    **decision,
                    "models_used": [
                        normalize_model_name(model) or model
                        for model in decision.get("models_used", [])
                    ],
                    "selected_model": normalize_model_name(
                        decision.get("selected_model")
                    )
                    or decision.get("selected_model"),
                }
                for decision in cache_data.get("decision_history", [])
                if isinstance(decision, dict)
            ]
            self.model_scores = defaultdict(
                float,
                {
                    normalize_model_name(model) or model: score
                    for model, score in cache_data.get("model_scores", {}).items()
                },
            )
            self.task_type_preferences = defaultdict(
                lambda: defaultdict(float),
                {
                    task: defaultdict(
                        float,
                        {
                            normalize_model_name(model) or model: score
                            for model, score in preferences.items()
                        },
                    )
                    for task, preferences in cache_data.get(
                        "task_type_preferences", {}
                    ).items()
                },
            )

            logger.info(
                f"Preferências carregadas: {len(self.decision_history)} decisões"
            )
        except Exception as e:
            logger.warning(f"Error loading preferences: {e}")


class ResponseCache:
    """Cache inteligente de responses de modelos"""

    def __init__(self, cache_dir: Optional[str] = None, max_size: int = 1000):
        """
        Initialise the response cache

        Args:
            cache_dir: Cache directory.
            max_size: Maximum cache size.
        """
        from aura_cli.core.paths import ArtifactLayout

        self.cache_dir = (
            Path(cache_dir) if cache_dir else ArtifactLayout().project("response_cache")
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.max_size = max_size

        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        self._cache_file = self.cache_dir / "responses.json"
        self._load_cache()

    def get(self, prompt_hash: str) -> Optional[Dict[str, Any]]:
        """Return a cached response, or None if not found."""
        result = self.cache.get(prompt_hash)
        if result is not None:
            self.cache.move_to_end(prompt_hash)
        return result

    def set(self, prompt_hash: str, response: Dict[str, Any]):
        """
        Armazena resposta no cache

        Args:
            prompt_hash: Hash do prompt
            response: Resposta para cachear
        """
        if len(self.cache) >= self.max_size:
            self.cache.popitem(last=False)

        self.cache[prompt_hash] = response
        self._save_cache()

    def hash_prompt(
        self, prompt: str, model: str, system_message: Optional[str] = None
    ) -> str:
        """Generate a unique hash for a prompt + model pair."""
        canonical_model = normalize_model_name(model) or model
        content = f"{canonical_model}:{system_message or ''}:{prompt}"
        return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()

    def _save_cache(self):
        """Persist response cache to disk."""
        try:
            cache_to_save = dict(list(self.cache.items())[-self.max_size :])

            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_to_save, f, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Error saving cache: {e}")

    def _load_cache(self):
        """Load response cache from disk."""
        if not self._cache_file.exists():
            return

        try:
            with open(self._cache_file, encoding="utf-8") as f:
                self.cache = json.load(f)

            logger.info(f"Cache loaded: {len(self.cache)} responses")
        except Exception as e:
            logger.warning(f"Error loading cache: {e}")


class AdvancedMultiModelIntelligence(MultiModelIntelligence):
    """Multi-Model Intelligence com cache e aprendizado"""

    def __init__(
        self,
        models: Optional[List[str]] = None,
        enable_cache: bool = True,
        enable_learning: bool = True,
    ):
        """
        Initialise the advanced multi-model intelligence

        Args:
            models: List of models
            enable_cache: Enable response caching.
            enable_learning: Enable learning.a apreference learning
        """
        super().__init__(models=models)

        self.enable_cache = enable_cache
        self.enable_learning = enable_learning

        if enable_cache:
            self.cache = ResponseCache()
        else:
            self.cache = None  # type: ignore[assignment]

        if enable_learning:
            self.learner = ModelPreferenceLearner()
        else:
            self.learner = None  # type: ignore[assignment]

    def smart_query_with_cache(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        ensemble_strategy: str = "best",
        task_type: str = "general",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Execute a smart query with cache and preference learning."""
        if use_cache and self.cache:
            prompt_hash = self.cache.hash_prompt(
                prompt, self.models[0] if self.models else "default", system_message
            )
            cached_response = self.cache.get(prompt_hash)

            if cached_response:
                logger.info("Resposta obtida do cache")
                return cached_response

        if self.learner:
            best_model = self.learner.get_best_model_for_task(task_type, self.models)
            if best_model:
                logger.info(f"Usando modelo preferido para {task_type}: {best_model}")

        responses = self.query_models(prompt, system_message)

        ensemble = self.create_ensemble(responses, strategy=ensemble_strategy)

        comparison = self.compare_responses(responses)

        result = {
            "best_response": {
                "model": ensemble.best_response.model,
                "content": ensemble.best_response.content,
                "quality_score": ensemble.best_response.quality_score,
                "quality": ensemble.best_response.quality.name,
                "latency_ms": ensemble.best_response.latency_ms,
                "tokens": ensemble.best_response.tokens_used,
            },
            "ensemble": {
                "consensus_score": ensemble.consensus_score,
                "agreement_level": ensemble.agreement_level,
                "selected_model": ensemble.selected_model,
                "reasoning": ensemble.reasoning,
            },
            "comparison": comparison,
            "cached": False,
        }

        if use_cache and self.cache:
            self.cache.set(prompt_hash, result)
            result["cached"] = True

        if self.learner:
            models_used = [r.model for r in responses]
            self.learner.record_decision(
                task_type=task_type,
                models_used=models_used,
                selected_model=ensemble.best_response.model,
            )

        return result

    def get_model_recommendation(self, task_type: str) -> Optional[str]:
        """Return a model recommendation for the given task type."""
        if not self.learner:
            return None

        return self.learner.get_best_model_for_task(task_type, self.models)

    def record_user_feedback(self, task_type: str, model: str, feedback: str):
        """Record user feedback for a model selection."""
        if self.learner:
            self.learner.record_decision(
                task_type=task_type,
                models_used=[normalize_model_name(model) or model],
                selected_model=normalize_model_name(model) or model,
                user_feedback=feedback,
            )


def smart_query_with_learning(
    prompt: str,
    models: Optional[List[str]] = None,
    system_message: Optional[str] = None,
    task_type: str = "general",
) -> Dict[str, Any]:
    """Execute a smart query with adaptive preference learning."""
    mmi = AdvancedMultiModelIntelligence(
        models=models, enable_cache=True, enable_learning=True
    )
    return mmi.smart_query_with_cache(prompt, system_message, task_type=task_type)


def get_model_recommendation(
    task_type: str, models: Optional[List[str]] = None
) -> Optional[str]:
    """Return a model recommendation for the given task type."""
    mmi = AdvancedMultiModelIntelligence(models=models, enable_learning=True)
    return mmi.get_model_recommendation(task_type)
