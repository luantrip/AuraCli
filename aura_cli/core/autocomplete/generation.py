"""
Auxiliary suggestion generation for autocomplete flows.

Offers local suggestion and completion strategies.letion for editing/command UX. It is a support capability, not a central pipeline of the
architecture. produto.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from aura_cli.core.autocomplete.classification import ClassificationResult, ContextType
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class GenerationStrategy(Enum):
    """Suggestion generation strategies enum."""

    CONTEXT_BASED = "context_based"
    TEMPLATE_BASED = "template_based"
    SNIPPET_BASED = "snippet_based"
    HYBRID = "hybrid"


@dataclass
class Suggestion:
    """Autocomplete suggestion (text, completion, score, type)."""

    text: str
    completion: str
    description: str = ""
    score: float = 0.0
    context_type: Optional[ContextType] = None


class AutocompleteGenerator:
    """Auxiliary autocomplete generator."""

    def __init__(
        self,
        strategy: GenerationStrategy = GenerationStrategy.HYBRID,
        use_ml_models: bool = True,
    ):
        """Initialise the autocomplete generator."""
        self.strategy = strategy
        self.use_ml_models = use_ml_models
        self.stats = get_stats()

        self.templates = self._load_templates()

        self._generation_model: Any = None
        self._generation_tokenizer = None
        self._model_loaded = False

        if use_ml_models:
            self._load_generation_model()

        logger.info(
            f"AutocompleteGenerator initialized (strategy: {strategy.value}, ML: {use_ml_models})"
        )

    def _load_generation_model(self) -> None:
        """Load the code generation model."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer

            model_name = "Salesforce/codet5-base"
            logger.info(f"Carregando modelo de geração: {model_name}")

            self._generation_tokenizer = AutoTokenizer.from_pretrained(  # nosec B615
                model_name, revision="main"
            )
            self._generation_model = AutoModelForCausalLM.from_pretrained(  # nosec B615
                model_name, revision="main"
            )
            self._generation_model.eval()

            self._model_loaded = True
            logger.info(f"Generation model loaded: {model_name}")

        except ImportError:
            logger.warning("transformers não instalado, code completion limitado")
            self._model_loaded = False
        except Exception as e:
            logger.warning(f"Error loading generation model: {e}, using fallback")
            self._model_loaded = False

    def generate(
        self,
        context: str,
        classification: ClassificationResult,
        prefix: str = "",
        max_suggestions: int = 10,
    ) -> List[Suggestion]:
        """Generate autocomplete suggestions for a context."""
        suggestions = []

        if self.strategy == GenerationStrategy.CONTEXT_BASED:
            suggestions = self._generate_context_based(context, classification, prefix)
        elif self.strategy == GenerationStrategy.TEMPLATE_BASED:
            suggestions = self._generate_template_based(classification, prefix)
        elif self.strategy == GenerationStrategy.SNIPPET_BASED:
            suggestions = self._generate_snippet_based(classification, prefix)
        else:
            suggestions = self._generate_hybrid(context, classification, prefix)

        suggestions.sort(key=lambda s: s.score, reverse=True)

        suggestions = suggestions[:max_suggestions]

        logger.debug(f"{len(suggestions)} sugestões geradas para prefixo '{prefix}'")

        self.stats.track_tool_usage("autocomplete_generation")

        return suggestions

    def _generate_context_based(
        self, context: str, classification: ClassificationResult, prefix: str
    ) -> List[Suggestion]:
        """Generate context-based suggestions."""
        suggestions = []

        import re

        func_pattern = r"\bdef\s+([a-z_][a-z0-9_]*)"
        functions = re.findall(func_pattern, context)

        var_pattern = r"\b([a-z_][a-z0-9_]*)\s*="
        variables = re.findall(var_pattern, context)

        class_pattern = r"\bclass\s+([A-Z][a-zA-Z0-9_]*)"
        classes = re.findall(class_pattern, context)

        all_names = list(set(functions + variables + classes))

        for name in all_names:
            if prefix.lower() in name.lower():
                score = 0.7
                if name.startswith(prefix):
                    score = 0.9

                suggestions.append(
                    Suggestion(
                        text=name,
                        completion=name,
                        description=f"From context: {name}",
                        score=score,
                        context_type=classification.context_type,
                    )
                )

        return suggestions

    def _generate_template_based(
        self, classification: ClassificationResult, prefix: str
    ) -> List[Suggestion]:
        """Generate template-based suggestions."""
        suggestions = []

        context_type = classification.context_type

        if context_type in self.templates:
            templates = self.templates[context_type]

            for template in templates:
                if prefix.lower() in template.lower():
                    suggestions.append(
                        Suggestion(
                            text=template,
                            completion=template,
                            description=f"Template for {context_type.value}",
                            score=0.8,
                            context_type=context_type,
                        )
                    )

        return suggestions

    def _generate_snippet_based(
        self, classification: ClassificationResult, prefix: str
    ) -> List[Suggestion]:
        """Generate reusable snippets from the bundled template catalog."""
        context_type = classification.context_type
        snippets = self.templates.get(context_type, [])
        prefix_lower = prefix.lower()
        return [
            Suggestion(
                text=snippet,
                completion=snippet,
                description=f"Snippet for {context_type.value}",
                score=0.75,
                context_type=context_type,
            )
            for snippet in snippets
            if not prefix_lower or prefix_lower in snippet.lower()
        ]

    def _generate_hybrid(
        self, context: str, classification: ClassificationResult, prefix: str
    ) -> List[Suggestion]:
        """Generate suggestions using a hybrid strategy."""
        suggestions = []

        context_suggestions = self._generate_context_based(
            context, classification, prefix
        )
        template_suggestions = self._generate_template_based(classification, prefix)

        if self.use_ml_models and self._model_loaded:
            ml_suggestions = self._generate_ml_based(context, prefix)
            suggestions.extend(ml_suggestions)

        all_suggestions = context_suggestions + template_suggestions + suggestions

        seen = set()
        unique = []
        for sug in all_suggestions:
            if sug.completion not in seen:
                seen.add(sug.completion)
                unique.append(sug)

        return unique

    def _generate_ml_based(
        self, context: str, prefix: str, max_suggestions: int = 5
    ) -> List[Suggestion]:
        """Generate suggestions using the ML model."""
        if (
            not self._model_loaded
            or not self._generation_model
            or not self._generation_tokenizer
        ):
            return []

        try:
            import torch

            input_text = context[-200:] + prefix

            inputs = self._generation_tokenizer(
                input_text, return_tensors="pt", truncation=True, max_length=256
            )

            with torch.no_grad():
                outputs = self._generation_model.generate(
                    inputs["input_ids"],
                    max_length=inputs["input_ids"].shape[1] + 20,
                    num_return_sequences=max_suggestions,
                    temperature=0.7,
                    do_sample=True,
                    pad_token_id=self._generation_tokenizer.pad_token_id,
                )

            suggestions = []
            for output in outputs:
                generated_text = self._generation_tokenizer.decode(
                    output[inputs["input_ids"].shape[1] :], skip_special_tokens=True
                )

                completion = generated_text.split("\n")[0].strip()
                if completion and len(completion) > 0:
                    suggestions.append(
                        Suggestion(
                            text=prefix + completion,
                            completion=completion,
                            description="ML-generated completion",
                            score=0.8,
                            context_type=None,
                        )
                    )

            logger.debug(f"Geradas {len(suggestions)} sugestões ML")
            return suggestions[:max_suggestions]

        except Exception as e:
            logger.debug(f"Error generating ML suggestions: {e}")
            return []

    def _load_templates(self) -> Dict[ContextType, List[str]]:
        """Load suggestion templates by context type."""
        return {
            ContextType.FUNCTION_DEFINITION: [
                "def function_name(param1, param2):",
                "async def async_function(param):",
                "def function_with_type_hints(param: str) -> str:",
            ],
            ContextType.CLASS_DEFINITION: [
                "class ClassName:",
                "class ClassName(BaseClass):",
                "class ClassName(metaclass=Meta):",
            ],
            ContextType.METHOD_CALL: [
                "object.method()",
                "object.method(param)",
                "object.method(param1, param2)",
            ],
            ContextType.VARIABLE_ASSIGNMENT: [
                "variable = value",
                "variable: type = value",
                "variable = function_call()",
            ],
            ContextType.CONDITIONAL: [
                "if condition:",
                "if condition:\n    pass",
                "if condition:\n    pass\nelse:\n    pass",
            ],
            ContextType.LOOP: [
                "for item in iterable:",
                "for i in range(n):",
                "while condition:",
            ],
        }
