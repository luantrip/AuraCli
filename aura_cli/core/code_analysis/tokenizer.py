"""Auxiliary code tokenizer for tooling and context support.

CodeTokenizer provides structure-preserving tokenisation for Python, JS, TS,
Java, C/C++, Go and Rust. Uses Hugging Face code-specialised tokenisers when
available; falls back to simple word-boundary tokenisation. Support library,
not a product-level subsystem.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


class Language(Enum):
    """Supported languages."""

    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    C = "c"
    GO = "go"
    RUST = "rust"
    UNKNOWN = "unknown"


@dataclass
class TokenInfo:
    """Token information (token, token_id, position, token_type)."""

    token: str
    token_id: int
    position: int
    type: Optional[str] = None


@dataclass
class TokenizationResult:
    """Tokenisation result (tokens, token_ids, attention_mask, language, stats)."""

    tokens: List[str] = field(default_factory=list)
    token_ids: List[int] = field(default_factory=list)
    attention_mask: List[int] = field(default_factory=list)
    language: Language = Language.UNKNOWN
    metadata: Dict[str, Any] = field(default_factory=dict)


class CodeTokenizer:
    """Structure-preserving tokeniser for Python, JS, TS, Java, Go, Rust."""

    def __init__(
        self, model_name: Optional[str] = None, language: Optional[Language] = None
    ):
        """Initialise the tokeniser."""
        self.model_name = model_name
        self.language = language
        self.stats = get_stats()
        self._tokenizer = None
        self._model_loaded = False

        self.language_models = {
            Language.PYTHON: "microsoft/graphcodebert-base",
            Language.JAVASCRIPT: "microsoft/graphcodebert-base",
            Language.TYPESCRIPT: "microsoft/graphcodebert-base",
            Language.JAVA: "microsoft/graphcodebert-base",
            Language.CPP: "microsoft/graphcodebert-base",
            Language.C: "microsoft/graphcodebert-base",
            Language.GO: "microsoft/graphcodebert-base",
            Language.RUST: "microsoft/graphcodebert-base",
        }

        self.default_model = "microsoft/graphcodebert-base"

        self._load_tokenizer()

        logger.info(f"CodeTokenizer initialized (model: {self.model_name or 'auto'})")

    def _load_tokenizer(self) -> None:
        """Load the HuggingFace tokeniser."""
        try:
            from transformers import AutoTokenizer

            if self.model_name:
                model_to_use = self.model_name
            elif self.language and self.language in self.language_models:
                model_to_use = self.language_models[self.language]
            else:
                model_to_use = self.default_model

            logger.info(f"Carregando tokenizador: {model_to_use}")

            self._tokenizer = AutoTokenizer.from_pretrained(  # nosec B615
                model_to_use, revision="main"
            )
            self.model_name = model_to_use
            self._model_loaded = True

            logger.info(f"Tokenizer loaded: {model_to_use}")

        except ImportError:
            logger.warning("transformers não instalado, tokenização limitada")
            self._model_loaded = False
        except Exception as e:
            logger.error(f"Error loading tokenizer: {e}", exc_info=True)
            self._model_loaded = False

    def tokenize(
        self, code: str, max_length: int = 512, return_offsets: bool = False
    ) -> TokenizationResult:
        """Tokenise a code string and return a TokeniseResult."""
        if not self._model_loaded or not self._tokenizer:
            return self._simple_tokenize(code)

        try:
            language = self.language or self._detect_language(code)

            encoding = self._tokenizer(
                code,
                return_tensors="pt",
                truncation=True,
                max_length=max_length,
                padding=True,
                return_offsets_mapping=return_offsets,
            )

            tokens = self._tokenizer.convert_ids_to_tokens(encoding["input_ids"][0])
            token_ids = encoding["input_ids"][0].tolist()
            attention_mask = encoding["attention_mask"][0].tolist()

            tokens_clean = [
                t for t in tokens if t not in ["<pad>", "<s>", "</s>", "[CLS]", "[SEP]"]
            ]

            result = TokenizationResult(
                tokens=tokens_clean,
                token_ids=token_ids,
                attention_mask=attention_mask,
                language=language,
                metadata={
                    "model": self.model_name,
                    "num_tokens": len(tokens_clean),
                    "max_length": max_length,
                },
            )

            logger.debug(f"Código tokenizado: {len(tokens_clean)} tokens")
            self.stats.track_tool_usage("code_tokenizer")

            return result

        except Exception as e:
            logger.error(f"Error tokenizing code: {e}", exc_info=True)
            return self._simple_tokenize(code)

    def _simple_tokenize(self, code: str) -> TokenizationResult:
        """Simple fallback tokenisation."""
        import re

        tokens = re.findall(r"\b\w+\b|[^\w\s]", code)
        language = self._detect_language(code)

        return TokenizationResult(
            tokens=tokens,
            token_ids=list(range(len(tokens))),
            attention_mask=[1] * len(tokens),
            language=language,
            metadata={"method": "simple", "num_tokens": len(tokens)},
        )

    def _detect_language(self, code: str) -> Language:
        """Detect the programming language of the code."""
        code_lower = code.lower()

        if any(
            keyword in code_lower
            for keyword in ["def ", "import ", "from ", "class ", "if __name__"]
        ):
            return Language.PYTHON

        if any(
            keyword in code_lower
            for keyword in ["function ", "const ", "let ", "var ", "=>"]
        ):
            if (
                "interface " in code_lower
                or "type " in code_lower
                or ": " in code_lower
            ):
                return Language.TYPESCRIPT
            return Language.JAVASCRIPT

        if any(
            keyword in code_lower
            for keyword in ["public class", "private ", "public static"]
        ):
            return Language.JAVA

        if any(keyword in code_lower for keyword in ["#include", "int main", "void "]):
            if "::" in code or "std::" in code_lower:
                return Language.CPP
            return Language.C

        if any(keyword in code_lower for keyword in ["package ", "func ", "import ("]):
            return Language.GO

        if any(keyword in code_lower for keyword in ["fn ", "let mut", "use ", "mod "]):
            return Language.RUST

        return Language.UNKNOWN

    def analyze_tokens(self, result: TokenizationResult) -> Dict[str, Any]:
        """Analyse extracted tokens and return statistics."""
        tokens = result.tokens

        analysis = {
            "total_tokens": len(tokens),
            "unique_tokens": len(set(tokens)),
            "avg_token_length": sum(len(t) for t in tokens) / max(len(tokens), 1),
            "language": result.language.value,
            "vocabulary_size": len(set(tokens)),
        }

        keywords = 0
        identifiers = 0
        operators = 0

        for token in tokens:
            if token in [
                "def",
                "class",
                "if",
                "else",
                "for",
                "while",
                "return",
                "import",
                "from",
            ]:
                keywords += 1
            elif token.isalnum() and not token.isdigit():
                identifiers += 1
            elif token in ["=", "+", "-", "*", "/", "==", "!=", "<", ">"]:
                operators += 1

        analysis["keywords"] = keywords
        analysis["identifiers"] = identifiers
        analysis["operators"] = operators

        logger.debug(f"Análise de tokens: {analysis}")

        return analysis
