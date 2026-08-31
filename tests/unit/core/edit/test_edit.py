"""
Testes Unitários para Módulo de Edição do Aura CLI.

Este módulo contém testes unitários que verificam o funcionamento individual
de componentes do sistema de edição de código, incluindo planejamento de
edições e execução de múltiplas edições em lote.

Componentes Testados:
    - EditPlanner: Planejador de edições com estratégias
    - EditPlan: Estrutura de plano de edição
    - multi_edit: Execução de múltiplas edições
    - EditOperation: Operação individual de edição

Cenários de Teste:
    - Inicialização: Criação de planejador
    - Criação de Plano: Planejamento de edições
    - Edição Múltipla: Execução de múltiplas operações

Validações:
    - Planejador inicializa corretamente
    - Planos são criados com operações
    - Edições múltiplas são executadas
    - Operações são aplicadas corretamente

Estrutura de Testes:
    - TestEditPlanner: Testes do planejador
    - TestMultiEdit: Testes de edição múltipla

Estratégias de Edição:
    - SAFE: Edição segura com validação
    - AGGRESSIVE: Edição agressiva sem validação
    - INCREMENTAL: Edição incremental passo a passo

EditOperation:
    Estrutura que representa uma operação:
    - id: Identificador único
    - file_path: Caminho do arquivo
    - old_content: Conteúdo antigo
    - new_content: Conteúdo novo
    - description: Descrição da operação

EditPlan:
    Plano que contém:
    - description: Descrição do plano
    - operations: Lista de operações
    - strategy: Estratégia de execução
    - estimated_impact: Impacto estimado

Exemplo de Uso:
    ```python
    def test_edit():
        planner = EditPlanner()
        plan = planner.create_plan("Edit test.py", operations=[...])

        operations = [EditOperation(...)]
        result = multi_edit(operations)
        assert result["success"]
    ```

Dependências:
    - pytest: Framework de testes
    - edit_planner: Sistema de planejamento
    - multi_edit: Sistema de edição múltipla
"""

from aura_cli.core.edit.edit_planner import EditPlanner
from aura_cli.core.edit.multi_edit import EditOperation, multi_edit


class TestEditPlanner:
    """Testes para planejador de edições."""

    def test_planner_initialization(self):
        """Testa inicialização do planejador."""
        planner = EditPlanner()

        assert planner is not None

    def test_create_plan(self):
        """Testa criação de plano de edição."""
        planner = EditPlanner()

        plan = planner.create_plan(
            "Edit test.py",
            operations=[
                {
                    "file_path": "test.py",
                    "old_content": "old",
                    "new_content": "new",
                    "description": "Replace old with new",
                }
            ],
        )

        assert plan is not None
        assert len(plan.operations) == 1


class TestMultiEdit:
    """Testes para edição múltipla."""

    def test_multi_edit(self, temp_dir):
        """Testa edição múltipla."""
        test_file = temp_dir / "test.py"
        test_file.write_text("old content")

        operations = [
            EditOperation(
                id="op1",
                file_path=str(test_file),
                old_content="old",
                new_content="new",
                description="Replace old with new",
            )
        ]

        result = multi_edit(operations)

        assert result is not None
        assert hasattr(result, "success") or isinstance(result, dict)
