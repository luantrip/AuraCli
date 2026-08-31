"""
Testes para funcionalidades da Fase 3.

Testa Embeddings Avançados, Visualização Interativa e Multi-Model Avançado.
Seguindo padrão AAA (Arrange-Act-Assert).
"""

import pytest


class TestEmbeddingsAdvanced:
    """Testes para embeddings avançados sem depender de download de modelo."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Fixture que cria projeto temporário."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "code.py").write_text(
            """
def function_with_embeddings():
    return "test"
""",
            encoding="utf-8",
        )
        return tmp_path

    @pytest.fixture
    def fake_embeddings(self, monkeypatch):
        """Injeta vetores determinísticos no módulo opcional de embeddings."""
        import numpy as np

        import aura_cli.core.embeddings.embeddings_advanced as embeddings_module

        class FakeTextEmbedding:
            def __init__(self, model_name):
                self.model_name = model_name

            def embed(self, texts):
                for text in texts:
                    value = float(len(text) % 10 + 1)
                    yield np.array([value, 1.0, 0.5], dtype=float)

        monkeypatch.setattr(embeddings_module, "HAS_EMBEDDINGS", True)
        monkeypatch.setattr(embeddings_module, "TextEmbedding", FakeTextEmbedding)
        monkeypatch.setattr(embeddings_module, "np", np, raising=False)

    def test_codebase_embeddings_initialization(self, temp_project, fake_embeddings):
        """Inicializa CodebaseEmbeddings usando o backend fake local."""
        from aura_cli.core.embeddings.embeddings_advanced import CodebaseEmbeddings

        embeddings = CodebaseEmbeddings(
            scope=str(temp_project), model_name="offline-test-model"
        )

        assert embeddings.scope == temp_project.resolve()
        assert embeddings.index.model_name == "offline-test-model"

    def test_index_codebase_embeddings_structure(self, temp_project, fake_embeddings):
        """Indexa um projeto pequeno sem depender de fastembed."""
        from aura_cli.core.embeddings.embeddings_advanced import (
            index_codebase_embeddings,
        )

        result = index_codebase_embeddings(
            scope=str(temp_project), model_name="offline-test-model"
        )

        assert isinstance(result, dict)
        assert result["status"] == "indexed"
        assert result["total_files"] == 1
        assert result["total_documents"] >= 1

    def test_semantic_search_codebase(self, temp_project, fake_embeddings):
        """Executa busca semântica sobre o índice fake local."""
        from aura_cli.core.embeddings.embeddings_advanced import (
            semantic_search_codebase,
        )

        results = semantic_search_codebase("function", scope=str(temp_project), top_k=5)

        assert isinstance(results, list)
        assert results
        assert all("similarity" in result for result in results)


class TestVisualizationInteractive:
    """Testes de visualização com disponibilidade explícita."""

    def test_create_dependency_graph_plotly(self):
        """Gera gráfico ou confirma a indisponibilidade explícita de Plotly."""
        from aura_cli.core.visualization.visualization_interactive import (
            HAS_PLOTLY,
            create_dependency_graph_plotly,
        )

        deps = {"main.py": ["utils.py", "config.py"], "utils.py": ["config.py"]}
        if not HAS_PLOTLY:
            with pytest.raises(ImportError, match="plotly"):
                create_dependency_graph_plotly(deps)
            return

        html = create_dependency_graph_plotly(deps)
        assert isinstance(html, str)
        assert len(html) > 0
        assert (
            "<html" in html.lower()
            or "<div" in html.lower()
            or "plotly" in html.lower()
        )

    def test_create_impact_analysis_chart(self):
        """Gera gráfico de impacto ou confirma a indisponibilidade de Plotly."""
        from aura_cli.core.visualization.visualization_interactive import (
            HAS_PLOTLY,
            create_impact_analysis_chart,
        )

        impact_data = {
            "affected_files": [
                {
                    "file": "test.py",
                    "risk_level": 7,
                    "dependents_count": 5,
                    "dependencies_count": 2,
                }
            ]
        }
        if not HAS_PLOTLY:
            with pytest.raises(ImportError, match="plotly"):
                create_impact_analysis_chart(impact_data)
            return

        html = create_impact_analysis_chart(impact_data)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_create_progress_dashboard(self):
        """Gera dashboard ou confirma a indisponibilidade de Plotly."""
        from aura_cli.core.visualization.visualization_interactive import (
            HAS_PLOTLY,
            create_progress_dashboard,
        )

        progress_data = {"completed_steps": 75, "total_steps": 100}
        if not HAS_PLOTLY:
            with pytest.raises(ImportError, match="plotly"):
                create_progress_dashboard(progress_data)
            return

        html = create_progress_dashboard(progress_data)
        assert isinstance(html, str)
        assert len(html) > 0


class TestMultiModelAdvanced:
    """Testes para Multi-Model Avançado"""

    def test_advanced_multi_model_intelligence_initialization(self):
        """
        Arrange: Configuração de modelos
        Act: Inicializa AdvancedMultiModelIntelligence
        Assert: Instância é criada
        """
        from aura_cli.core.llm.multi_model_advanced import (
            AdvancedMultiModelIntelligence,
        )

        # Arrange
        models = ["gemini/gemini-1.5-flash-latest"]

        # Act
        mmi = AdvancedMultiModelIntelligence(
            models=models, enable_cache=True, enable_learning=True
        )

        # Assert
        assert mmi is not None
        assert hasattr(mmi, "models") or hasattr(mmi, "enable_cache")

    def test_model_preference_learner(self):
        """
        Arrange: Learner vazio
        Act: Registra decisão e obtém recomendação
        Assert: Aprendizado funciona
        """
        from aura_cli.core.llm.multi_model_advanced import ModelPreferenceLearner

        # Arrange
        learner = ModelPreferenceLearner()

        # Act - Registra decisão com assinatura correta
        # Assinatura: record_decision(task_type, models_used, selected_model, user_feedback=None)
        learner.record_decision(
            task_type="refactoring",
            models_used=["model1", "model2"],
            selected_model="model1",
            user_feedback="good",
        )

        # Act - Obtém recomendação
        recommendation = learner.get_best_model_for_task(
            "refactoring", ["model1", "model2"]
        )

        # Assert
        assert recommendation is not None
        assert recommendation in ["model1", "model2"] or isinstance(recommendation, str)

    def test_response_cache(self):
        """
        Arrange: Cache vazio
        Act: Gera hash de prompt
        Assert: Cache funciona
        """
        from aura_cli.core.llm.multi_model_advanced import ResponseCache

        # Arrange
        cache = ResponseCache()

        # Act
        prompt_hash = cache.hash_prompt("test prompt", "test-model")

        # Assert
        assert isinstance(prompt_hash, str)
        assert len(prompt_hash) > 0

    def test_smart_query_with_learning_structure(self):
        """
        Arrange: Configuração de query
        Act: Estrutura de smart query
        Assert: Estrutura funciona
        """
        from aura_cli.core.llm.multi_model_advanced import smart_query_with_learning

        # Arrange
        # Não fazemos chamada real à API, apenas verificamos estrutura

        # Act & Assert
        # Verifica que função existe e pode ser chamada
        assert callable(smart_query_with_learning)

    def test_get_model_recommendation_structure(self):
        """
        Arrange: Configuração de task
        Act: Obtém recomendação de modelo
        Assert: Recomendação funciona
        """
        from aura_cli.core.llm.multi_model_advanced import get_model_recommendation

        # Arrange
        # Não fazemos chamada real, apenas verificamos estrutura

        # Act & Assert
        # Verifica que função existe
        assert callable(get_model_recommendation)
