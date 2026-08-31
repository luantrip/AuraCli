"""
Multi-model fallback and ensemble operations for Aura CLI.

Handles querying multiple models in parallel, comparing responses, and selecting
the best one. Does NOT perform initial model selection — that belongs to TaskRouter.
"""

import concurrent.futures
from dataclasses import dataclass
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Tuple

from aura_cli.core.llm.model_utils import (
    get_default_multi_model_candidates,
    normalize_model_name,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

try:
    import litellm

    HAS_LITELLM = True
except ImportError:
    HAS_LITELLM = False
    logger.warning("litellm não disponível. Multi-model intelligence limitado.")


class ModelQuality(Enum):
    """Qualidade da resposta do modelo"""

    EXCELLENT = 5
    GOOD = 4
    ACCEPTABLE = 3
    POOR = 2
    INVALID = 1


@dataclass
class ModelResponse:
    """Resposta de um modelo individual"""

    model: str
    content: str
    quality_score: float
    quality: ModelQuality
    tokens_used: Optional[int] = None
    latency_ms: Optional[float] = None
    metadata: Dict[str, Any] = None  # type: ignore[assignment]

    def __post_init__(self):
        """Post-initialization setup for dataclass fields."""
        if self.metadata is None:
            self.metadata = {}


@dataclass
class EnsembleResult:
    """Resultado do ensemble de models"""

    best_response: ModelResponse
    all_responses: List[ModelResponse]
    consensus_score: float
    agreement_level: str  # "high", "medium", "low"
    selected_model: str
    reasoning: str


class MultiModelIntelligence:
    """Multi-model LLM routing with automatic fallback and quality scoring."""

    def __init__(self, models: Optional[List[str]] = None):
        """
        Initialise the multi-model intelligence

        Args:
            models: List of models to use. If None, uses defaults.
        """
        if not HAS_LITELLM:
            raise ImportError("litellm é necessário para multi-model intelligence")

        self.default_models = get_default_multi_model_candidates()
        requested_models = models or self.default_models
        self.models = [
            canonical
            for model in requested_models
            if (canonical := normalize_model_name(model)) and canonical != "auto"
        ] or self.default_models
        logger.info(
            f"Multi-Model Intelligence initialized with {len(self.models)} models"
        )

    def query_models(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        max_workers: int = 3,
        timeout: float = 60.0,
    ) -> List[ModelResponse]:
        """Query a list of models and return the best response."""
        logger.info(f"Consultando {len(self.models)} models simultaneamente")

        responses = []

        def query_single_model(model: str) -> Optional[ModelResponse]:
            """Consulta um modelo individual"""
            start_time = time.time()
            try:
                messages = []
                if system_message:
                    messages.append({"role": "system", "content": system_message})
                messages.append({"role": "user", "content": prompt})

                response = litellm.completion(
                    model=model, messages=messages, timeout=timeout
                )

                latency_ms = (time.time() - start_time) * 1000
                if not response.choices:
                    raise ValueError(
                        f"Empty response from model {model}: no choices returned"
                    )
                content = response.choices[0].message.content
                tokens_used = (
                    response.usage.total_tokens if hasattr(response, "usage") else None
                )

                quality_score, quality = self._evaluate_response_quality(content, model)

                return ModelResponse(
                    model=model,
                    content=content,
                    quality_score=quality_score,
                    quality=quality,
                    tokens_used=tokens_used,
                    latency_ms=latency_ms,
                    metadata={"raw_response": str(response)},
                )
            except Exception as e:
                logger.warning(f"Error querying model {model}: {e}")
                return None

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_model = {
                executor.submit(query_single_model, model): model
                for model in self.models
            }

            for future in concurrent.futures.as_completed(future_to_model):
                response = future.result()
                if response:
                    responses.append(response)

        logger.info(
            f"Recebidas {len(responses)} respostas de {len(self.models)} models"
        )
        return responses

    def _evaluate_response_quality(
        self, content: str, model: str
    ) -> Tuple[float, ModelQuality]:
        """Evaluate response quality and return a score 0–1."""
        if not content or len(content.strip()) == 0:
            return 0.0, ModelQuality.INVALID

        score = 0.0

        length_score = min(len(content) / 100, 1.0)
        score += length_score * 0.2

        has_structure = any(marker in content for marker in ["```", "`", "#", "*", "-"])
        structure_score = 0.3 if has_structure else 0.1
        score += structure_score

        completeness_keywords = [
            "implement",
            "function",
            "class",
            "example",
            "solution",
            "approach",
        ]
        has_keywords = sum(
            1 for kw in completeness_keywords if kw.lower() in content.lower()
        )
        completeness_score = min(has_keywords / len(completeness_keywords), 1.0) * 0.3
        score += completeness_score

        has_placeholders = any(ph in content for ph in ["TODO", "FIXME", "XXX", "..."])
        if has_placeholders:
            score *= 0.7

        model_bonus = {
            "gpt-4o": 0.1,
            "gpt-4-turbo": 0.1,
            "claude-sonnet-4": 0.1,
            "claude-opus-4": 0.1,
            "gpt-oss-120b": 0.0,
            "gemma-4-27b-it": 0.09,
            "gemma-4-26b-a4b-it": 0.08,
            "nemotron-super-49b": 0.1,
        }
        for model_name, bonus in model_bonus.items():
            if model_name in model.lower():
                score += bonus
                break

        score = min(score, 1.0)

        if score >= 0.8:
            quality = ModelQuality.EXCELLENT
        elif score >= 0.6:
            quality = ModelQuality.GOOD
        elif score >= 0.4:
            quality = ModelQuality.ACCEPTABLE
        elif score >= 0.2:
            quality = ModelQuality.POOR
        else:
            quality = ModelQuality.INVALID

        return score, quality

    def compare_responses(self, responses: List[ModelResponse]) -> Dict[str, Any]:
        """Compare responses from multiple models for the same prompt."""
        if not responses:
            return {"error": "Nenhuma resposta para comparar"}

        sorted_responses = sorted(
            responses, key=lambda r: r.quality_score, reverse=True
        )

        avg_score = sum(r.quality_score for r in responses) / len(responses)
        latency_responses = [r for r in responses if r.latency_ms is not None]
        avg_latency = (
            sum(r.latency_ms or 0.0 for r in latency_responses) / len(latency_responses)
            if latency_responses
            else 0.0
        )
        total_tokens = sum(r.tokens_used for r in responses if r.tokens_used)

        similarity_scores = self._calculate_similarity(responses)
        consensus = (
            sum(similarity_scores) / len(similarity_scores)
            if similarity_scores
            else 0.0
        )

        return {
            "total_models": len(responses),
            "best_model": sorted_responses[0].model,
            "best_score": sorted_responses[0].quality_score,
            "average_score": avg_score,
            "consensus_score": consensus,
            "average_latency_ms": avg_latency,
            "total_tokens": total_tokens,
            "responses": [
                {
                    "model": r.model,
                    "score": r.quality_score,
                    "quality": r.quality.name,
                    "latency_ms": r.latency_ms,
                    "tokens": r.tokens_used,
                }
                for r in sorted_responses
            ],
        }

    def _calculate_similarity(self, responses: List[ModelResponse]) -> List[float]:
        """Calculate similarity between responses (simplified)."""
        if len(responses) < 2:
            return []

        similarities = []
        for i in range(len(responses)):
            for j in range(i + 1, len(responses)):
                r1, r2 = responses[i], responses[j]
                words1 = set(r1.content.lower().split())
                words2 = set(r2.content.lower().split())

                if len(words1) == 0 or len(words2) == 0:
                    similarity = 0.0
                else:
                    intersection = words1 & words2
                    union = words1 | words2
                    similarity = (
                        len(intersection) / len(union) if len(union) > 0 else 0.0
                    )

                similarities.append(similarity)

        return similarities

    def create_ensemble(
        self, responses: List[ModelResponse], strategy: str = "best"
    ) -> EnsembleResult:
        """
        Create an ensemble of responses

        Args:
            responses: List of responses
            strategy: "best" (bestr resposta), "consensus" (consenso), "weighted" (ponderado)

        Returns:
            Resultado do ensemble
        """
        if not responses:
            raise ValueError("Nenhuma resposta fornecida para ensemble")

        if strategy == "best":
            best = max(responses, key=lambda r: r.quality_score)
            consensus_score = best.quality_score
            agreement_level = (
                "high"
                if consensus_score > 0.7
                else "medium"
                if consensus_score > 0.5
                else "low"
            )
            reasoning = f"Selecionada melhor resposta baseada em qualidade (score: {best.quality_score:.2f})"

        elif strategy == "consensus":
            similarities = []
            for i, r1 in enumerate(responses):
                avg_sim = 0.0
                for j, r2 in enumerate(responses):
                    if i != j:
                        words1 = set(r1.content.lower().split())
                        words2 = set(r2.content.lower().split())
                        if words1 and words2:
                            intersection = words1 & words2
                            union = words1 | words2
                            avg_sim += (
                                len(intersection) / len(union)
                                if len(union) > 0
                                else 0.0
                            )
                avg_sim /= (len(responses) - 1) if len(responses) > 1 else 1
                similarities.append((avg_sim, r1))

            best = max(similarities, key=lambda x: x[0])[1]
            consensus_score = max(similarities, key=lambda x: x[0])[0]
            agreement_level = (
                "high"
                if consensus_score > 0.5
                else "medium"
                if consensus_score > 0.3
                else "low"
            )
            reasoning = f"Selecionada resposta com maior consenso (similaridade: {consensus_score:.2f})"

        elif strategy == "weighted":
            total_weight = sum(r.quality_score for r in responses)
            if total_weight > 0:
                best = max(responses, key=lambda r: r.quality_score)
                consensus_score = total_weight / len(responses)
                agreement_level = (
                    "high"
                    if consensus_score > 0.6
                    else "medium"
                    if consensus_score > 0.4
                    else "low"
                )
                reasoning = (
                    f"Selecionada resposta ponderada (peso total: {total_weight:.2f})"
                )
            else:
                best = responses[0]
                consensus_score = 0.0
                agreement_level = "low"
                reasoning = (
                    "Nenhuma resposta de qualidade suficiente, usando primeira resposta"
                )
        else:
            raise ValueError(f"Estratégia desconhecida: {strategy}")

        return EnsembleResult(
            best_response=best,
            all_responses=responses,
            consensus_score=consensus_score,
            agreement_level=agreement_level,
            selected_model=best.model,
            reasoning=reasoning,
        )

    def smart_query(
        self,
        prompt: str,
        system_message: Optional[str] = None,
        ensemble_strategy: str = "best",
        return_all: bool = False,
    ) -> Dict[str, Any]:
        """Execute a query with smart model selection and caching."""
        responses = self.query_models(prompt, system_message)

        if not responses:
            return {"error": "Nenhuma resposta recebida dos models"}

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
        }

        if return_all:
            result["all_responses"] = [  # type: ignore[assignment]
                {
                    "model": r.model,
                    "content": r.content,
                    "quality_score": r.quality_score,
                    "quality": r.quality.name,
                }
                for r in responses
            ]

        return result


def query_multiple_models(
    prompt: str,
    models: Optional[List[str]] = None,
    system_message: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query multiple models in parallel and return all responses."""
    if not HAS_LITELLM:
        raise ImportError("litellm é necessário para multi-model queries")

    mmi = MultiModelIntelligence(models=models)
    responses = mmi.query_models(prompt, system_message)

    return [
        {
            "model": r.model,
            "content": r.content,
            "quality_score": r.quality_score,
            "quality": r.quality.name,
            "latency_ms": r.latency_ms,
            "tokens": r.tokens_used,
        }
        for r in responses
    ]


def compare_model_responses(
    prompt: str,
    models: Optional[List[str]] = None,
    system_message: Optional[str] = None,
) -> Dict[str, Any]:
    """Compare responses from different models and rank them."""
    if not HAS_LITELLM:
        raise ImportError("litellm é necessário para multi-model comparison")

    mmi = MultiModelIntelligence(models=models)
    responses = mmi.query_models(prompt, system_message)
    return mmi.compare_responses(responses)


def smart_model_query(
    prompt: str,
    models: Optional[List[str]] = None,
    system_message: Optional[str] = None,
    ensemble_strategy: str = "best",
) -> Dict[str, Any]:
    """Execute a smart query with automatic model selection."""
    if not HAS_LITELLM:
        raise ImportError("litellm é necessário para smart model queries")

    mmi = MultiModelIntelligence(models=models)
    return mmi.smart_query(prompt, system_message, ensemble_strategy=ensemble_strategy)
