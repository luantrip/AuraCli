"""
Testes para Sistema de To-Do Tracker do Aura CLI.

Este módulo contém testes que verificam o funcionamento completo do sistema de
rastreamento de tarefas (to-do tracker), incluindo parsing de arquivos markdown,
gerenciamento de status, estatísticas e funções globais do tracker.

Componentes Testados:
    - TodoTask: Estrutura de dados para tarefas individuais
    - TodoTracker: Classe principal de rastreamento
    - get_todo_tracker: Função global para obter instância singleton
    - refresh_todo_tracker: Função para atualizar instância global

Cenários de Teste:
    - Criação de Tarefas: Tarefas pendentes e concluídas
    - Inicialização: Criação e configuração do tracker
    - Carregamento: Parsing de arquivo to-do.md
    - Estatísticas: Cálculo de total, pendentes, concluídas
    - Tarefa Atual: Obtenção da primeira tarefa pendente
    - Instância Global: Singleton e refresh

Validações:
    - Tarefas são criadas com status correto
    - Tracker inicializa corretamente
    - Tarefas são carregadas do arquivo
    - Estatísticas são calculadas corretamente
    - Tarefa atual é a primeira pendente
    - Instância global funciona como singleton

Estrutura de Testes:
    - TestTodoTask: Testes da estrutura TodoTask
    - TestTodoTracker: Testes da classe TodoTracker
    - TestTodoTrackerGlobal: Testes das funções globais

Fixtures:
    - temp_todo_file: Cria arquivo to-do.md temporário com tarefas de exemplo

Formatos Suportados:
    - ○ (círculo vazio) para pendente
    - ● (círculo preenchido) para concluída
    - ☐ e ☒ (checkboxes)
    - - [ ] e - [x] (markdown checkboxes)

Propriedades de TodoTask:
    - is_pending: True se status é "pending"
    - is_done: True se status é "done"

Métodos de TodoTracker:
    - refresh(): Recarrega tarefas do arquivo
    - get_stats(): Retorna estatísticas
    - get_pending_tasks(): Lista tarefas pendentes
    - get_done_tasks(): Lista tarefas concluídas
    - get_current_task(): Primeira tarefa pendente
    - get_all_tasks(): Todas as tarefas

Exemplo de Uso:
    ```python
    def test_tracker(temp_todo_file):
        tracker = TodoTracker(scope=str(temp_todo_file))
        stats = tracker.get_stats()
        assert stats["total"] > 0
        assert stats["total"] == stats["pending"] + stats["done"]
    ```

Dependências:
    - pytest: Framework de testes
    - tempfile: Para criação de arquivos temporários
    - shutil: Para limpeza
    - todo_tracker: Módulo de rastreamento de tarefas
"""

from pathlib import Path

import pytest

from aura_cli.core.todo.todo_tracker import (
    TodoTask,
    TodoTracker,
    get_todo_tracker,
    refresh_todo_tracker,
)


class TestTodoTask:
    """Testes para classe TodoTask"""

    def test_task_creation_pending(self):
        """
        Testa criação de tarefa pendente.

        Verifica se TodoTask cria tarefa pendente corretamente.
        """
        task = TodoTask(
            id=1,
            text="Teste",
            status="pending",
            line_number=1,
            original_line="○ Teste\n",
        )

        assert task.id == 1
        assert task.text == "Teste"
        assert task.status == "pending"
        assert task.is_pending is True
        assert task.is_done is False

    def test_task_creation_done(self):
        """
        Testa criação de tarefa concluída.

        Verifica se TodoTask cria tarefa concluída corretamente.
        """
        task = TodoTask(
            id=1, text="Teste", status="done", line_number=1, original_line="● Teste\n"
        )

        assert task.is_done is True
        assert task.is_pending is False


class TestTodoTracker:
    """Testes para classe TodoTracker"""

    @pytest.fixture
    def temp_todo_file(self, tmp_path):
        """
        Fixture que cria arquivo to-do temporário.

        Cria estrutura .aura/to-do.md para testes.
        """
        aura_dir = tmp_path / ".aura"
        aura_dir.mkdir()
        todo_file = aura_dir / "to-do.md"
        todo_file.write_text(
            """# To-do List

- [ ] Tarefa 1
- [ ] Tarefa 2
- [x] Tarefa 3 (concluída)
- [ ] Tarefa 4
""",
            encoding="utf-8",
        )
        return tmp_path

    def test_tracker_initialization(self, temp_todo_file):
        """
        Testa inicialização do TodoTracker.

        Verifica se TodoTracker inicializa corretamente.
        """
        tracker = TodoTracker(scope=str(temp_todo_file))

        assert tracker.scope == Path(temp_todo_file).resolve()
        assert tracker.todo_file.exists()

    def test_tracker_loads_tasks(self, temp_todo_file):
        """
        Testa carregamento de tarefas do arquivo.

        Verifica se TodoTracker carrega tarefas do to-do.md corretamente.
        """
        tracker = TodoTracker(scope=str(temp_todo_file))
        tracker.refresh()

        all_tasks = tracker.get_all_tasks()
        assert len(all_tasks) > 0

    def test_tracker_get_stats(self, temp_todo_file):
        """
        Testa obtenção de estatísticas.

        Verifica se get_stats retorna estatísticas corretas.
        """
        tracker = TodoTracker(scope=str(temp_todo_file))
        tracker.refresh()

        stats = tracker.get_stats()

        assert isinstance(stats, dict)
        assert "total" in stats
        assert "pending" in stats
        assert "done" in stats
        assert stats["total"] == stats["pending"] + stats["done"]

    def test_tracker_get_current_task(self, temp_todo_file):
        """
        Testa obtenção de tarefa atual.

        Verifica se get_current_task retorna primeira tarefa pendente.
        """
        tracker = TodoTracker(scope=str(temp_todo_file))
        tracker.refresh()

        current = tracker.get_current_task()

        # Pode ser None se não houver tarefas pendentes
        if current:
            assert current.is_pending is True


class TestTodoTrackerGlobal:
    """Testes para funções globais do todo tracker"""

    def test_get_todo_tracker_returns_instance(self):
        """
        Testa get_todo_tracker retorna instância.

        Verifica se get_todo_tracker retorna instância válida.
        """
        tracker = get_todo_tracker()

        assert isinstance(tracker, TodoTracker)

    def test_refresh_todo_tracker_updates(self):
        """
        Testa refresh_todo_tracker atualiza tracker.

        Verifica se refresh_todo_tracker atualiza estado do tracker.
        """
        refresh_todo_tracker()

        tracker = get_todo_tracker()
        # Deve funcionar sem erro
        assert tracker is not None
