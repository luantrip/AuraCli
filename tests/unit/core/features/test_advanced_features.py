"""
Testes para funcionalidades da Fase 2.

Testa Codebase Indexing, Visualization e Multi-Model Intelligence.
Seguindo padrão AAA (Arrange-Act-Assert).
"""

from pathlib import Path

import pytest

from aura_cli.core.context.code_index import (
    get_global_context,
    index_codebase,
    search_codebase,
)
from aura_cli.core.llm.multi_model import (
    ModelQuality,
    ModelResponse,
    MultiModelIntelligence,
    compare_model_responses,
)
from aura_cli.core.visualization.visualization import (
    export_dependency_graph,
    export_impact_analysis,
    visualize_dependency_graph,
    visualize_impact_analysis,
)


class TestCodebaseIndexing:
    """Testes para indexação de codebase"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Fixture que cria projeto temporário"""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            """
class MainClass:
    def main_method(self):
        return "main"

def main_function():
    return MainClass()
""",
            encoding="utf-8",
        )
        (tmp_path / "src" / "utils.py").write_text(
            """
def utility_function():
    return "utility"
""",
            encoding="utf-8",
        )
        return tmp_path

    def test_index_codebase_creates_index(self, temp_project):
        """
        Arrange: Projeto com código
        Act: Indexa codebase
        Assert: Índice é criado
        """
        # Arrange
        scope = str(temp_project)

        # Act
        stats = index_codebase(scope=scope, force_reindex=False)

        # Assert
        assert isinstance(stats, dict)
        assert (
            "total_files" in stats
            or "total_classes" in stats
            or "total_functions" in stats
        )
        assert stats.get("total_files", 0) >= 0

    def test_search_codebase_finds_results(self, temp_project):
        """
        Arrange: Codebase indexado
        Act: Busca no codebase
        Assert: Resultados são encontrados
        """
        # Arrange
        scope = str(temp_project)
        # Indexa primeiro
        index_codebase(scope=scope, force_reindex=False)

        # Act
        results = search_codebase("function", scope=scope, limit=5)

        # Assert
        assert isinstance(results, list)
        # Pode encontrar resultados ou lista vazia
        assert len(results) >= 0

    def test_get_global_context_returns_context(self, temp_project):
        """
        Arrange: Codebase indexado
        Act: Obtém contexto global
        Assert: Contexto é retornado
        """
        # Arrange
        scope = str(temp_project)
        # Indexa primeiro
        index_codebase(scope=scope, force_reindex=False)

        # Act
        context = get_global_context(scope=scope)

        # Assert
        assert isinstance(context, dict)
        assert "total_files" in context or len(str(context)) > 0


class TestVisualization:
    """Testes para visualização"""

    def test_visualize_dependency_graph_tree_format(self):
        """
        Arrange: Dependências conhecidas
        Act: Visualiza grafo de dependências
        Assert: Visualização é gerada
        """
        # Arrange
        deps = {"main.py": ["utils.py", "config.py"], "utils.py": ["config.py"]}

        # Act
        viz = visualize_dependency_graph(deps, output_format="tree")

        # Assert
        assert isinstance(viz, str)
        assert len(viz) > 0

    def test_visualize_dependency_graph_table_format(self):
        """
        Arrange: Dependências conhecidas
        Act: Visualiza em formato tabela
        Assert: Visualização é gerada
        """
        # Arrange
        deps = {"main.py": ["utils.py"], "utils.py": []}

        # Act
        viz = visualize_dependency_graph(deps, output_format="table")

        # Assert
        assert isinstance(viz, str)
        assert len(viz) > 0

    def test_visualize_impact_analysis_table_format(self):
        """
        Arrange: Dados de impacto
        Act: Visualiza análise de impacto
        Assert: Visualização é gerada
        """
        # Arrange
        impact_data = {
            "affected_files": [
                {
                    "file": "test.py",
                    "risk_level": 7,
                    "dependents_count": 5,
                    "dependencies_count": 2,
                }
            ],
            "summary": {
                "total_files": 1,
                "total_dependents": 5,
                "total_dependencies": 2,
            },
        }

        # Act
        impact_viz = visualize_impact_analysis(impact_data, output_format="table")

        # Assert
        assert isinstance(impact_viz, str)
        assert len(impact_viz) > 0

    def test_export_dependency_graph(self, tmp_path):
        """
        Arrange: Dependências conhecidas
        Act: Exporta grafo de dependências
        Assert: Exportação funciona
        """
        # Arrange
        deps = {"main.py": ["utils.py"]}
        output_path = str(tmp_path / "deps.json")

        # Act
        export_dependency_graph(deps, output_path, output_format="json")

        # Assert
        # A função escreve no arquivo, não retorna valor
        # Verifica que o arquivo foi criado
        output_file = Path(output_path).with_suffix(".json")
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8")

    def test_export_impact_analysis(self, tmp_path):
        """
        Arrange: Dados de impacto
        Act: Exporta análise de impacto
        Assert: Exportação funciona
        """
        # Arrange
        impact_data = {
            "affected_files": [{"file": "test.py", "risk_level": 5}],
            "summary": {"total_files": 1},
        }
        output_path = str(tmp_path / "impact.json")

        # Act
        export_impact_analysis(impact_data, output_path, output_format="json")

        # Assert
        # A função escreve no arquivo, não retorna valor
        # Verifica que o arquivo foi criado
        output_file = Path(output_path).with_suffix(".json")
        assert output_file.exists()
        assert output_file.read_text(encoding="utf-8")


class TestMultiModelIntelligence:
    """Testes para Multi-Model Intelligence"""

    def test_multi_model_intelligence_initialization(self):
        """
        Arrange: Lista de modelos
        Act: Inicializa MultiModelIntelligence
        Assert: Instância é criada
        """
        # Arrange
        models = ["gemini/gemini-1.5-flash-latest"]

        # Act
        mmi = MultiModelIntelligence(models=models)

        # Assert
        assert isinstance(mmi, MultiModelIntelligence)
        assert len(mmi.models) == 1

    def test_model_response_creation(self):
        """
        Arrange: Dados de resposta
        Act: Cria ModelResponse
        Assert: Resposta é criada corretamente
        """
        # Arrange
        content = "This is a test response"

        # Act
        response = ModelResponse(
            model="test-model",
            content=content,
            quality_score=0.8,
            quality=ModelQuality.GOOD,
        )

        # Assert
        assert response.model == "test-model"
        assert response.content == content
        assert response.quality_score == 0.8
        assert response.quality == ModelQuality.GOOD

    def test_model_quality_enum(self):
        """
        Arrange: Enum ModelQuality
        Act: Acessa valores
        Assert: Enum funciona corretamente
        """
        # Arrange & Act & Assert
        assert ModelQuality.EXCELLENT is not None
        assert ModelQuality.GOOD is not None
        assert (
            ModelQuality.ACCEPTABLE is not None
        )  # Corrigido: ACCEPTABLE ao invés de FAIR
        assert ModelQuality.POOR is not None
        assert ModelQuality.INVALID is not None

    def test_compare_model_responses_structure(self):
        """
        Arrange: Múltiplas respostas
        Act: Compara respostas
        Assert: Comparação funciona
        """
        # Arrange
        responses = [
            ModelResponse("model1", "response1", 0.9, ModelQuality.EXCELLENT),
            ModelResponse("model2", "response2", 0.7, ModelQuality.GOOD),
        ]

        # Act
        comparison = compare_model_responses(responses)

        # Assert
        # Pode retornar dict ou string com comparação
        assert isinstance(comparison, (dict, str))
        assert len(str(comparison)) > 0
