"""Advanced embedding generator for semantic-memory and code-similarity flows.

Supports fastembed (ONNX, default BAAI/bge-small-en-v1.5), OpenAI, Hugging
Face, CodeBERT and a dependency-free TF-IDF Simple fallback.
CodeBERTa is disabled (incompatible with current transformers API) and falls
back to SIMPLE automatically.
"""

from enum import Enum
from typing import Any, List, Optional

import numpy as np

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class EmbeddingModel(Enum):
    """Available embedding models."""

    FASTEMBED = "fastembed"
    OPENAI = "openai"
    HUGGINGFACE = "huggingface"
    CODEBERT = "codebert"  # microsoft/codebert-base
    CODEBERTA = "codeberta"  # huggingface/CodeBERTa-small-v1
    SIMPLE = "simple"  # Fallback simples


class EmbeddingGenerator:
    """Generates text/code embeddings using specialised models."""

    def __init__(
        self,
        model: EmbeddingModel = EmbeddingModel.SIMPLE,
        dimension: int = 384,
        model_name: Optional[str] = None,
    ):
        """Initialise the embedding generator."""
        self.model = model
        self.dimension = dimension
        self.model_name = model_name
        self.stats = get_stats()
        self._model_instance: Any = None
        self._tokenizer: Any = None

        self._load_model()

        logger.info(
            f"EmbeddingGenerator initialized (model: {model.value}, dimension: {dimension})"
        )

    def _load_model(self) -> None:
        """Load the embedding model."""
        if self.model == EmbeddingModel.FASTEMBED:
            try:
                from fastembed import TextEmbedding

                model_name = self.model_name or "BAAI/bge-small-en-v1.5"
                self._model_instance = TextEmbedding(model_name=model_name)
                # Determine dimension from a test embedding
                test_emb = next(iter(self._model_instance.embed(["test"])))
                self.dimension = len(test_emb)
                logger.info(f"fastembed model loaded: {model_name}")
            except ImportError:
                logger.warning("fastembed não instalado, usando modelo simples")
                self.model = EmbeddingModel.SIMPLE
        elif self.model == EmbeddingModel.OPENAI:
            logger.info("Modelo OpenAI requer configuração de API key")
        elif self.model == EmbeddingModel.CODEBERT:
            try:
                from transformers import AutoModel, AutoTokenizer

                model_name = self.model_name or "microsoft/codebert-base"
                logger.info(f"Carregando CodeBERT: {model_name}")

                self._tokenizer = AutoTokenizer.from_pretrained(  # nosec B615
                    model_name, revision="main"
                )
                self._model_instance = AutoModel.from_pretrained(  # nosec B615
                    model_name, revision="main"
                )
                self._model_instance.eval()

                self.dimension = 768
                logger.info(f"CodeBERT model loaded: {model_name}")
            except ImportError:
                logger.warning("transformers não instalado, usando modelo simples")
                self.model = EmbeddingModel.SIMPLE
            except Exception as e:
                logger.error(f"Error loading CodeBERT: {e}", exc_info=True)
                self.model = EmbeddingModel.SIMPLE
        elif self.model == EmbeddingModel.CODEBERTA:
            # NOTE: CodeBERTa (huggingface/CodeBERTa-small-v1) is no longer compatible
            # - Newer transformers try to access "additional_chat_templates" on the repo
            # - That path does not exist, causing a RemoteEntryNotFoundError (404)
            #
            # This was generating a very noisy stacktrace in the CLI every time an
            # advanced memory feature tried to initialize this embedding model.
            #
            # To keep Aura stable and avoid surprising network calls, we now treat
            # CODEBERTA as a disabled / deprecated option and immediately fall back
            # to the SIMPLE embedding model.
            logger.warning(
                "Embedding model CODEBERTA (huggingface/CodeBERTa-small-v1) "
                "está desativado devido a incompatibilidades com a API do Hugging Face. "
                "Usando fallback SIMPLE."
            )
            self.model = EmbeddingModel.SIMPLE
        elif self.model == EmbeddingModel.HUGGINGFACE:
            try:
                from transformers import AutoModel, AutoTokenizer

                model_name = self.model_name or "BAAI/bge-small-en-v1.5"
                logger.info(f"Carregando modelo HuggingFace genérico: {model_name}")

                self._tokenizer = AutoTokenizer.from_pretrained(  # nosec B615
                    model_name, revision="main"
                )
                self._model_instance = AutoModel.from_pretrained(  # nosec B615
                    model_name, revision="main"
                )
                self._model_instance.eval()

                if hasattr(self._model_instance.config, "hidden_size"):
                    self.dimension = self._model_instance.config.hidden_size
                else:
                    self.dimension = 384

                logger.info(
                    f"HuggingFace model loaded: {model_name} (dimension: {self.dimension})"
                )
            except ImportError:
                logger.warning("transformers não instalado, usando modelo simples")
                self.model = EmbeddingModel.SIMPLE
            except Exception as e:
                logger.error(f"Error loading HuggingFace model: {e}", exc_info=True)
                self.model = EmbeddingModel.SIMPLE

    def generate(self, text: str) -> np.ndarray:
        """Generate an embedding for a text string."""
        if self.model == EmbeddingModel.FASTEMBED and self._model_instance:
            embedding = next(iter(self._model_instance.embed([text])))
            return np.array(embedding)
        elif self.model == EmbeddingModel.OPENAI:
            return self._simple_embedding(text)
        elif self.model in [
            EmbeddingModel.CODEBERT,
            EmbeddingModel.CODEBERTA,
            EmbeddingModel.HUGGINGFACE,
        ]:
            if self._model_instance and self._tokenizer:
                return self._generate_huggingface_embedding(text)
            else:
                logger.warning("HuggingFace model not loaded, using fallback")
                return self._simple_embedding(text)
        else:
            return self._simple_embedding(text)

    def _generate_huggingface_embedding(self, text: str) -> np.ndarray:
        """Generate an embedding using a HuggingFace model."""
        try:
            import torch

            inputs = self._tokenizer(
                text, return_tensors="pt", truncation=True, max_length=512, padding=True
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

                embedding_np = embedding.squeeze().cpu().numpy()

                norm = np.linalg.norm(embedding_np)
                if norm > 0:
                    embedding_np = embedding_np / norm

                return embedding_np

        except Exception as e:
            logger.error(f"Error generating HuggingFace embedding: {e}", exc_info=True)
            return self._simple_embedding(text)

    def generate_batch(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Generate embeddings for a batch of text strings."""
        if self.model == EmbeddingModel.FASTEMBED and self._model_instance:
            embeddings = list(self._model_instance.embed(texts))
            return np.array(embeddings)
        elif self.model in [
            EmbeddingModel.CODEBERT,
            EmbeddingModel.CODEBERTA,
            EmbeddingModel.HUGGINGFACE,
        ]:
            if self._model_instance and self._tokenizer:
                return self._generate_huggingface_batch(texts, batch_size)
            else:
                logger.warning("HuggingFace model not loaded, using fallback")
                return np.array([self.generate(text) for text in texts])
        else:
            return np.array([self.generate(text) for text in texts])

    def _generate_huggingface_batch(
        self, texts: List[str], batch_size: int = 32
    ) -> np.ndarray:
        """Generate embeddings in batch using a HuggingFace model."""
        try:
            import torch

            all_embeddings = []

            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i : i + batch_size]

                inputs = self._tokenizer(
                    batch_texts,
                    return_tensors="pt",
                    truncation=True,
                    max_length=512,
                    padding=True,
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
                    batch_embeddings = sum_embeddings / sum_mask

                    batch_np = batch_embeddings.cpu().numpy()
                    for j in range(len(batch_np)):
                        norm = np.linalg.norm(batch_np[j])
                        if norm > 0:
                            batch_np[j] = batch_np[j] / norm

                    all_embeddings.append(batch_np)

            if all_embeddings:
                return np.vstack(all_embeddings)
            else:
                return np.array([])

        except Exception as e:
            logger.error(
                f"Error generating HuggingFace embeddings in batch: {e}", exc_info=True
            )
            return np.array([self.generate(text) for text in texts])

    def _simple_embedding(self, text: str) -> np.ndarray:
        """Generate a simple fallback embedding."""
        import hashlib

        text_hash = hashlib.md5(text.encode(), usedforsecurity=False).hexdigest()

        vector = np.zeros(self.dimension)

        for i, char in enumerate(text_hash[: self.dimension]):
            vector[i] = ord(char) / 255.0

        vector[0] = len(text) / 1000.0
        vector[1] = text.count(" ") / max(len(text), 1)

        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm

        return vector


def get_embedding_model(
    model: EmbeddingModel = EmbeddingModel.SIMPLE, dimension: int = 384
) -> EmbeddingGenerator:
    """
    Create an embedding generator for the requested model and dimension.

    Args:
        model: Embedding model to use
        dimension: Vector dimension

    Returns:
        EmbeddingGenerator instance
    """
    return EmbeddingGenerator(model=model, dimension=dimension)
