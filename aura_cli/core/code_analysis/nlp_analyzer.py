"""Auxiliary NLP-style code analyser for tooling and context enrichment.

NLPAnalyzer supports classify_code(), summarize_code(), complexity analysis
and feature extraction. Uses Hugging Face Transformers when available;
falls back to AST-based heuristics. Support library — not a product-level
semantic centre.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


class ComplexityLevel(Enum):
    """Complexity levels."""

    VERY_SIMPLE = "very_simple"
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"
    VERY_COMPLEX = "very_complex"


class FunctionType(Enum):
    """Function types."""

    GETTER = "getter"
    SETTER = "setter"
    FACTORY = "factory"
    TRANSFORM = "transform"
    VALIDATOR = "validator"
    PROCESSOR = "processor"
    HELPER = "helper"
    UNKNOWN = "unknown"


@dataclass
class CodeClassification:
    """
    Code classification.

    Attributes:
        function_type: Function type
        complexity: Complexity level
        intent: Code intent
        confidence: Confidence (0-1)
    """

    function_type: FunctionType
    complexity: ComplexityLevel
    intent: str
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CodeSummary:
    """NLP-derived code summary (summary, key_points, complexity, intent)."""

    summary: str
    key_points: List[str] = field(default_factory=list)
    complexity: ComplexityLevel = ComplexityLevel.MODERATE
    suggestions: List[str] = field(default_factory=list)


class NLPAnalyzer:
    """Analyses code using NLP to extract intent and structure."""

    def __init__(self, model_name: Optional[str] = None):
        """Initialise the NLP analyser."""
        self.model_name = model_name
        self.stats = get_stats()
        self._model_loaded = False
        self._tokenizer = None
        self._model_instance: Any = None
        self._load_error: Any = None

        self.default_model = "microsoft/codebert-base"

        logger.info(
            f"NLPAnalyzer initialized (model: {self.model_name or 'auto'}, lazy loading enabled)"
        )

    def _load_model(self) -> bool:
        """Load the NLP model."""
        if self._model_loaded:
            return True

        if self._load_error and not isinstance(self._load_error, ImportError):
            return False

        try:
            from transformers import AutoModel, AutoTokenizer

            model_to_use = self.model_name or self.default_model
            logger.info(f"Carregando modelo para análise NLP: {model_to_use}")

            self._tokenizer = AutoTokenizer.from_pretrained(  # nosec B615
                model_to_use, revision="main"
            )
            self._model_instance = AutoModel.from_pretrained(  # nosec B615
                model_to_use, revision="main"
            )
            self._model_instance.eval()

            self.model_name = model_to_use
            self._model_loaded = True
            self._load_error = None

            logger.info(f"NLP model loaded: {model_to_use}")
            return True

        except ImportError:
            logger.warning(
                "transformers não instalado, análise NLP limitada (usando heurísticas)"
            )
            self._model_loaded = False
            self._load_error = ImportError("transformers não instalado")
            return False
        except Exception as e:
            error_msg = str(e)
            if (
                "torch.load" in error_msg
                or "CVE-2025-32434" in error_msg
                or "torch to at least v2.6" in error_msg
            ):
                logger.warning(
                    "⚠️  Análise NLP avançada não disponível: torch>=2.6.0 requerido mas ainda não lançado. "
                    "Usando análise heurística (funcionalidades básicas continuam disponíveis). "
                    "Quando torch 2.6.0 estiver disponível, execute: pip install --upgrade torch"
                )
            else:
                logger.warning(
                    f"Error loading NLP model (using heuristic analysis): {e}. "
                    f"Funcionalidades básicas continuam disponíveis."
                )
            self._model_loaded = False
            self._load_error = e
            return False

    def classify_code(
        self, code: str, context: Optional[str] = None
    ) -> CodeClassification:
        """Classify code and return its type."""
        function_type = self._classify_function_type(code)
        complexity = self._analyze_complexity(code)
        intent = self._extract_intent(code)

        if not self._model_loaded:
            self._load_model()

        if self._model_loaded:
            try:
                self._get_code_embedding(code)
            except Exception as e:
                logger.debug(f"Error using model for classification: {e}")

        classification = CodeClassification(
            function_type=function_type,
            complexity=complexity,
            intent=intent,
            confidence=0.7,
            metadata={"method": "heuristic", "model_available": self._model_loaded},
        )

        logger.debug(f"Código classificado: {function_type.value}, {complexity.value}")
        self.stats.track_tool_usage("nlp_classify")

        return classification

    def summarize_code(self, code: str, max_length: int = 100) -> CodeSummary:
        """Summarise code as a compact description."""
        if not self._model_loaded:
            self._load_model()

        summary = self._extract_summary(code)
        key_points = self._extract_key_points(code)
        complexity = self._analyze_complexity(code)
        suggestions = self._generate_suggestions(code)

        if self._model_loaded:
            try:
                pass
            except Exception as e:
                logger.debug(f"Error using model for summarization: {e}")

        result = CodeSummary(
            summary=summary[:max_length],
            key_points=key_points[:5],
            complexity=complexity,
            suggestions=suggestions[:3],
        )

        logger.debug(f"Código sumarizado: {len(summary)} caracteres")
        self.stats.track_tool_usage("nlp_summarize")

        return result

    def _classify_function_type(self, code: str) -> FunctionType:
        """Classify the function type."""
        code_lower = code.lower()

        if any(
            pattern in code_lower
            for pattern in ["return self.", "return ", "get_", "fetch_"]
        ) and ("=" not in code or code.count("=") == 1):
            return FunctionType.GETTER

        if any(
            pattern in code_lower for pattern in ["self.", " = ", "set_", "update_"]
        ) and ("return" not in code_lower or code_lower.count("return") <= 1):
            return FunctionType.SETTER

        if (
            any(
                pattern in code_lower
                for pattern in ["create_", "make_", "build_", "new "]
            )
            and "return" in code_lower
        ):
            return FunctionType.FACTORY

        if any(
            pattern in code_lower
            for pattern in ["transform", "convert", "map", "filter"]
        ):
            return FunctionType.TRANSFORM

        if any(
            pattern in code_lower
            for pattern in ["validate", "check", "verify", "is_valid"]
        ):
            return FunctionType.VALIDATOR

        if any(
            pattern in code_lower for pattern in ["process", "handle", "execute", "run"]
        ):
            return FunctionType.PROCESSOR

        return FunctionType.UNKNOWN

    def _analyze_complexity(self, code: str) -> ComplexityLevel:
        """Analyse code complexity."""
        lines = code.split("\n")
        num_lines = len([line for line in lines if line.strip()])

        num_ifs = code.count("if ")
        num_loops = code.count("for ") + code.count("while ")
        num_try = code.count("try:")
        num_nested = code.count("    ")

        complexity_score = (
            num_lines * 0.1
            + num_ifs * 2
            + num_loops * 3
            + num_try * 2
            + (num_nested / max(num_lines, 1)) * 10
        )

        if complexity_score < 5:
            return ComplexityLevel.VERY_SIMPLE
        elif complexity_score < 15:
            return ComplexityLevel.SIMPLE
        elif complexity_score < 30:
            return ComplexityLevel.MODERATE
        elif complexity_score < 50:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.VERY_COMPLEX

    def _extract_intent(self, code: str) -> str:
        """Extract the code intent."""
        code_lower = code.lower()

        intents = []

        if "read" in code_lower or "load" in code_lower or "get" in code_lower:
            intents.append("read")
        if "write" in code_lower or "save" in code_lower or "set" in code_lower:
            intents.append("write")
        if "transform" in code_lower or "convert" in code_lower:
            intents.append("transform")
        if "validate" in code_lower or "check" in code_lower:
            intents.append("validate")
        if "process" in code_lower or "handle" in code_lower:
            intents.append("process")

        return ", ".join(intents) if intents else "unknown"

    def _extract_summary(self, code: str) -> str:
        """Extract a code summary."""
        if '"""' in code:
            docstring_start = code.find('"""')
            docstring_end = code.find('"""', docstring_start + 3)
            if docstring_end > docstring_start:
                docstring = code[docstring_start + 3 : docstring_end].strip()
                return docstring

        import re

        func_match = re.search(r"def\s+([a-z_][a-z0-9_]*)", code, re.IGNORECASE)
        if func_match:
            func_name = func_match.group(1)
            return f"Função {func_name}: {self._extract_intent(code)}"

        lines = [
            line.strip()
            for line in code.split("\n")
            if line.strip() and not line.strip().startswith("#")
        ]
        if lines:
            return lines[0][:100]

        return "Código não documentado"

    def _extract_key_points(self, code: str) -> List[str]:
        """Extract key points from code."""
        points = []

        import re

        func_match = re.search(r"def\s+([a-z_][a-z0-9_]*)", code, re.IGNORECASE)
        if func_match:
            points.append(f"Define função: {func_match.group(1)}")

        param_match = re.search(r"def\s+\w+\s*\((.*?)\)", code, re.DOTALL)
        if param_match:
            params = param_match.group(1).strip()
            if params:
                points.append(f"Parâmetros: {params[:50]}")

        if "return" in code:
            return_match = re.search(r"return\s+(.+?)(?:\n|$)", code)
            if return_match:
                points.append(f"Retorna: {return_match.group(1).strip()[:50]}")

        if "if " in code:
            points.append("Contém condicionais")
        if "for " in code or "while " in code:
            points.append("Contém loops")
        if "try:" in code:
            points.append("Contém tratamento de exceções")

        return points

    def _generate_suggestions(self, code: str) -> List[str]:
        """Generate improvement suggestions."""
        suggestions = []

        if '"""' not in code and "'''" not in code:
            suggestions.append("Adicionar docstring")

        if (
            "def " in code
            and ":" not in code.split("def ")[1].split("(")[0]
            and not any(hint in code for hint in ["str", "int", "bool", "List", "Dict"])
        ):
            suggestions.append("Adicionar type hints")
        complexity = self._analyze_complexity(code)
        if complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.VERY_COMPLEX]:
            suggestions.append("Considerar refatorar para reduzir complexidade")

        if "try:" not in code and ("open(" in code or "requests." in code):
            suggestions.append("Considerar adicionar tratamento de exceções")

        return suggestions

    def _get_code_embedding(self, code: str) -> Any:
        """Get the code embedding from the model."""
        if not self._model_loaded or not self._tokenizer or not self._model_instance:
            return None

        try:
            import torch

            inputs = self._tokenizer(
                code, return_tensors="pt", truncation=True, max_length=512, padding=True
            )

            with torch.no_grad():
                outputs = self._model_instance(**inputs)
                embeddings = outputs.last_hidden_state
                attention_mask = inputs["attention_mask"]
                mask_expanded = (
                    attention_mask.unsqueeze(-1).expand(embeddings.size()).float()
                )
                sum_embeddings = torch.sum(embeddings * mask_expanded, dim=1)
                sum_mask = torch.clamp(mask_expanded.sum(1), min=1e-9)
                embedding = sum_embeddings / sum_mask

                return embedding.squeeze().cpu().numpy()

        except Exception as e:
            logger.debug(f"Error generating embedding: {e}")
            return None
