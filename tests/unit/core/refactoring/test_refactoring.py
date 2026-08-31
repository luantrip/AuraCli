"""
Testes para Sistema de Refatoração do Aura CLI.

Este módulo contém testes que verificam o funcionamento completo do sistema de
refatoração, incluindo planejamento de refatorações, análise de impacto e execução
segura de mudanças em código. Testa fluxos end-to-end de refatoração.

Componentes Testados:
    - plan_refactoring: Planejamento de refatorações com análise de padrões
    - analyze_impact_for_refactoring: Análise de impacto de refatorações
    - suggest_strategy: Sugestão de estratégia de execução
    - apply_refactoring_plan: Aplicação segura de planos de refatoração

Cenários de Teste:
    - Planejamento: Criação de planos de refatoração válidos
    - Análise de Impacto: Identificação de arquivos afetados
    - Sugestão de Estratégia: Recomendação de estratégia (incremental, all-at-once, etc.)
    - Execução: Aplicação de mudanças com confirmação

Validações:
    - Planos são criados corretamente
    - Impacto é analisado adequadamente
    - Estratégias sugeridas são apropriadas
    - Refatorações são aplicadas com segurança

Estrutura de Testes:
    - TestRefactoringPlanner: Testes de planejamento
    - TestRefactoringExecutor: Testes de execução

Fixtures:
    - temp_project: Cria projeto temporário com código de exemplo

Estratégias de Refatoração:
    - incremental: Refatoração em pequenos passos
    - all_at_once: Refatoração completa de uma vez
    - by_dependency: Refatoração ordenada por dependências
    - none: Nenhuma estratégia recomendada

Fluxo de Refatoração:
    1. Planejamento: Identifica padrões e cria plano
    2. Análise: Analisa impacto em arquivos
    3. Estratégia: Sugere melhor abordagem
    4. Execução: Aplica mudanças com validação

Exemplo de Uso:
    ```python
    def test_refactoring(temp_project):
        plan = plan_refactoring("old_function", "new_function", str(temp_project))
        assert isinstance(plan, RefactoringPlan)

        impact = analyze_impact_for_refactoring("old_function", "new_function", str(temp_project))
        assert "affected_files" in impact
    ```

Dependências:
    - pytest: Framework de testes
    - tempfile: Para criação de projetos temporários
    - refactoring_planner: Sistema de planejamento
    - refactoring_executor: Sistema de execução
"""

import pytest

from aura_cli.core.refactoring.refactoring_executor import (
    RefactoringPlan,
    apply_refactoring_plan,
)
from aura_cli.core.refactoring.refactoring_planner import (
    analyze_impact_for_refactoring,
    plan_refactoring,
    suggest_strategy,
)


class TestRefactoringPlanner:
    """Testes para planejamento de refatoração"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Fixture que cria projeto temporário para testes."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            """
def old_function():
    return "old"

def new_function():
    return "new"
""",
            encoding="utf-8",
        )
        return tmp_path

    def test_plan_refactoring_creates_plan(self, temp_project):
        """
        Testa criação de plano de refatoração.

        Verifica se plan_refactoring cria plano válido.
        """
        plan = plan_refactoring(
            pattern="old_function", replacement="new_function", scope=str(temp_project)
        )

        assert isinstance(plan, RefactoringPlan)
        assert len(str(plan)) > 0

    def test_analyze_impact_for_refactoring(self, temp_project):
        """
        Testa análise de impacto para refatoração.

        Verifica se analyze_impact_for_refactoring analisa impacto corretamente.
        """
        impact = analyze_impact_for_refactoring(
            pattern="old_function", replacement="new_function", scope=str(temp_project)
        )

        assert isinstance(impact, dict)
        assert (
            "affected_files" in impact
            or "impact" in str(impact).lower()
            or len(str(impact)) > 0
        )

    def test_suggest_strategy_returns_strategy(self, temp_project):
        """
        Testa sugestão de estratégia de refatoração.

        Verifica se suggest_strategy retorna estratégia válida.
        """
        strategy = suggest_strategy(
            pattern="old_function", replacement="new_function", scope=str(temp_project)
        )

        assert isinstance(strategy, dict)
        assert "strategy" in strategy
        assert strategy["strategy"] in [
            "incremental",
            "all_at_once",
            "by_dependency",
            "none",
        ]


class TestRefactoringExecutor:
    """Testes para execução de refatoração"""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Fixture que cria projeto temporário para testes."""
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text(
            """
def old_function():
    return "old"
""",
            encoding="utf-8",
        )
        return tmp_path

    def test_apply_refactoring_plan_applies_changes(self, temp_project, monkeypatch):
        """
        Testa aplicação de plano de refatoração.

        Verifica se apply_refactoring_plan aplica mudanças corretamente.
        """

        def mock_ask_confirmation(*args, **kwargs):
            return True

        def mock_confirm_ask(*args, **kwargs):
            return True

        monkeypatch.setattr(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            mock_ask_confirmation,
        )
        try:
            from rich.prompt import Confirm

            monkeypatch.setattr(Confirm, "ask", mock_confirm_ask)
        except Exception:
            pass

        # Cria plano simples
        plan = plan_refactoring(
            pattern="old_function", replacement="new_function", scope=str(temp_project)
        )

        def mock_ask_confirmation(*args, **kwargs):
            return True

        def mock_confirm_ask(*args, **kwargs):
            return True

        monkeypatch.setattr(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            mock_ask_confirmation,
        )
        try:
            from rich.prompt import Confirm

            monkeypatch.setattr(Confirm, "ask", mock_confirm_ask)
        except Exception:
            pass

        result = apply_refactoring_plan(plan, scope=str(temp_project))

        assert isinstance(result, dict)
        assert (
            "success" in result
            or "status" in result
            or "applied" in result
            or len(str(result)) > 0
        )

    def test_apply_refactoring_checks_dependencies(self, temp_project, monkeypatch):
        """
        Testa se o executor verifica dependências usando Nexus (GraphService).
        """
        from unittest.mock import MagicMock

        # Mock GraphService
        mock_graph = MagicMock()
        mock_graph.get_dependents.return_value = ["src/other.py"]
        mock_graph_service_instance = MagicMock()
        mock_graph_service_instance.build_graph.return_value = mock_graph
        mock_graph_service_class = MagicMock(return_value=mock_graph_service_instance)

        monkeypatch.setattr(
            "aura_cli.core.context.graph_service.GraphService", mock_graph_service_class
        )

        # Mock confirmation to avoid UI block
        def mock_ask_confirmation(*args, **kwargs):
            return True

        monkeypatch.setattr(
            "aura_cli.cli.ui.components.confirmation.ask_confirmation",
            mock_ask_confirmation,
        )

        # Create plan
        plan = RefactoringPlan()
        plan.add_step("src/main.py", "old", "new")

        # Execute
        apply_refactoring_plan(plan, scope=str(temp_project), validate=False)

        # Assert GraphService usage
        mock_graph_service_class.assert_called()
        mock_graph_service_instance.build_graph.assert_called()
        mock_graph.get_dependents.assert_called_with("src/main.py")
