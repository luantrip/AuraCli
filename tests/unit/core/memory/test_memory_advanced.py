"""
Testes Unitários para Sistema de Memória Avançada do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes do sistema de memória avançada, incluindo armazenamento vetorial,
geração de embeddings e busca semântica usando similaridade de vetores.

Componentes Testados:
    - VectorStorage: Armazenamento e busca de vetores
    - VectorDocument: Documento com embedding vetorial
    - EmbeddingGenerator: Geração de embeddings de texto
    - EmbeddingModel: Modelos de embedding suportados
    - SemanticSearch: Sistema de busca semântica
    - SearchQuery: Query de busca semântica

Cenários de Teste:
    - Inicialização: Criação de storage, generator e search
    - Criação de Índice: Criação de índices vetoriais
    - Adição e Busca: Adição de documentos e busca por similaridade
    - Geração de Embeddings: Geração individual e em batch
    - Indexação e Busca Semântica: Fluxo completo de indexação e busca

Validações:
    - Storage inicializa corretamente
    - Índices são criados com dimensões corretas
    - Documentos são adicionados e encontrados
    - Embeddings são gerados corretamente
    - Busca semântica retorna resultados relevantes

Estrutura de Testes:
    - TestVectorStorage: Testes do armazenamento vetorial
    - TestEmbeddingGenerator: Testes da geração de embeddings
    - TestSemanticSearch: Testes da busca semântica

Modelos de Embedding:
    - SIMPLE: Modelo simples (fallback)
    - FASTEMBED: fastembed (BAAI/bge-small-en-v1.5)
    - OPENAI: OpenAI embeddings
    - HUGGINGFACE: Modelos HuggingFace
    - CODEBERT: CodeBERT para código

Busca Semântica:
    Utiliza similaridade de cosseno:
    - Converte query em embedding
    - Calcula similaridade com documentos indexados
    - Retorna top-k resultados mais similares
    - Ordena por score de similaridade

VectorDocument:
    Documento com:
    - doc_id: Identificador único
    - content: Conteúdo do documento
    - vector: Embedding vetorial
    - metadata: Metadados adicionais

Exemplo de Uso:
    ```python
    def test_memory():
        storage = VectorStorage()
        storage.create_index("test", dimension=128)

        generator = EmbeddingGenerator()
        embedding = generator.generate("Test text")

        storage.add_document("test", "doc1", "Content", embedding)
        results = storage.search("test", embedding, top_k=1)
    ```

Dependências:
    - pytest: Framework de testes
    - numpy: Para operações vetoriais
    - vector_storage: Sistema de armazenamento vetorial
    - embeddings: Sistema de geração de embeddings
    - semantic_search: Sistema de busca semântica
"""

import numpy as np

from aura_cli.core.memory_advanced.embeddings import EmbeddingGenerator, EmbeddingModel
from aura_cli.core.memory_advanced.semantic_search import SearchQuery, SemanticSearch
from aura_cli.core.memory_advanced.vector_storage import VectorStorage


class TestVectorStorage:
    """Testes para VectorStorage."""

    def test_storage_initialization(self, temp_dir):
        """Testa inicialização do armazenamento."""
        storage = VectorStorage(storage_path=str(temp_dir))

        assert storage.storage_path.exists()
        assert len(storage.indices) == 0

    def test_create_index(self):
        """Testa criação de índice."""
        storage = VectorStorage()

        index = storage.create_index("test_index", dimension=128)

        assert index.index_id == "test_index"
        assert index.dimension == 128
        assert "test_index" in storage.indices

    def test_add_and_search_document(self):
        """Testa adição e busca de documento."""
        storage = VectorStorage()
        storage.create_index("test", dimension=128)

        # Adiciona documento
        vector = np.random.rand(128)
        storage.add_document("test", "doc1", "Test content", vector)

        # Busca
        results = storage.search("test", vector, top_k=1)

        assert len(results) == 1
        assert results[0][0].doc_id == "doc1"


class TestEmbeddingGenerator:
    """Testes para EmbeddingGenerator."""

    def test_generator_initialization(self):
        """Testa inicialização do gerador."""
        generator = EmbeddingGenerator(model=EmbeddingModel.SIMPLE, dimension=128)

        assert generator.model == EmbeddingModel.SIMPLE
        assert generator.dimension == 128

    def test_generate_embedding(self):
        """Testa geração de embedding."""
        generator = EmbeddingGenerator(dimension=128)

        embedding = generator.generate("Test text")

        assert embedding.shape == (128,)
        assert np.all(np.isfinite(embedding))

    def test_generate_batch(self):
        """Testa geração em batch."""
        generator = EmbeddingGenerator(dimension=128)

        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = generator.generate_batch(texts)

        assert embeddings.shape == (3, 128)


class TestSemanticSearch:
    """Testes para SemanticSearch."""

    def test_search_initialization(self):
        """Testa inicialização do sistema de busca."""
        search = SemanticSearch(index_id="test")

        assert search.index_id == "test"
        assert search.embedding_generator is not None

    def test_index_and_search(self):
        """Testa indexação e busca."""
        search = SemanticSearch(index_id="test")

        # Indexa documento
        search.index_document("doc1", "Python is a programming language")

        # Busca
        query = SearchQuery(query_text="What is Python?", top_k=1)
        results = search.search(query)

        assert len(results) > 0
        assert results[0].doc_id == "doc1"
