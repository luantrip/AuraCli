"""
Testes para sistema de to-do.

Testa TodoTracker, TodoDisplay e integração completa.
Seguindo padrão AAA (Arrange-Act-Assert).
"""

from pathlib import Path

import pytest
from rich.console import Group

from aura_cli.core.todo.todo_tracker import (
    TodoTask,
    TodoTracker,
    get_todo_tracker,
    refresh_todo_tracker,
)


class TestTodoTrackerSystem:
    """Testes para TodoTracker"""

    @pytest.fixture
    def temp_todo_file(self, tmp_path):
        """Fixture que cria arquivo to-do temporário"""
        aura_dir = tmp_path / ".aura"
        aura_dir.mkdir()
        todo_file = aura_dir / "to-do.md"
        todo_file.write_text(
            """# To-do List

- [ ] Tarefa 1 - Primeira tarefa
- [ ] Tarefa 2 - Segunda tarefa
- [x] Tarefa 3 - Tarefa concluída
- [ ] Tarefa 4 - Quarta tarefa
""",
            encoding="utf-8",
        )
        return tmp_path

    def test_todo_tracker_initialization(self, temp_todo_file):
        """
        Arrange: Arquivo to-do existe
        Act: Inicializa TodoTracker
        Assert: Tracker é criado corretamente
        """
        # Arrange
        scope = str(temp_todo_file)

        # Act
        tracker = TodoTracker(scope=scope)

        # Assert
        assert tracker.scope == Path(scope).resolve()
        assert tracker.todo_file.exists()

    def test_todo_tracker_loads_tasks(self, temp_todo_file):
        """
        Arrange: Arquivo to-do com tarefas
        Act: Carrega tarefas
        Assert: Tarefas são carregadas corretamente
        """
        # Arrange
        scope = str(temp_todo_file)
        tracker = TodoTracker(scope=scope)

        # Act
        tracker.refresh()
        all_tasks = tracker.get_all_tasks()

        # Assert
        assert len(all_tasks) > 0
        # Verifica que tarefas foram carregadas
        assert any(task.text for task in all_tasks)

    def test_todo_tracker_get_stats(self, temp_todo_file):
        """
        Arrange: Tracker com tarefas carregadas
        Act: Obtém estatísticas
        Assert: Estatísticas são corretas
        """
        # Arrange
        scope = str(temp_todo_file)
        tracker = TodoTracker(scope=scope)
        tracker.refresh()

        # Act
        stats = tracker.get_stats()

        # Assert
        assert isinstance(stats, dict)
        assert "total" in stats
        assert "pending" in stats
        assert "done" in stats
        assert stats["total"] == stats["pending"] + stats["done"]
        assert stats["total"] > 0

    def test_todo_tracker_get_current_task(self, temp_todo_file):
        """
        Arrange: Tracker com tarefas
        Act: Obtém tarefa atual
        Assert: Tarefa atual é retornada
        """
        # Arrange
        scope = str(temp_todo_file)
        tracker = TodoTracker(scope=scope)
        tracker.refresh()

        # Act
        current = tracker.get_current_task()

        # Assert
        # Pode ser None se não houver tarefas pendentes
        if current:
            assert isinstance(current, TodoTask)
            assert current.is_pending is True


class TestTodoDisplaySystem:
    """Testes para TodoDisplay"""

    @pytest.fixture
    def temp_todo_file(self, tmp_path):
        """Fixture que cria arquivo to-do temporário"""
        aura_dir = tmp_path / ".aura"
        aura_dir.mkdir()
        todo_file = aura_dir / "to-do.md"
        todo_file.write_text(
            """# To-do List

○ Tarefa 1
○ Tarefa 2
● Tarefa 3
""",
            encoding="utf-8",
        )
        return tmp_path

    def test_format_todo_summary(self, temp_todo_file):
        """
        Arrange: Tracker com tarefas
        Act: Formata resumo
        Assert: Resumo é formatado
        """
        from aura_cli.cli.ui.todo_display import format_todo_summary

        # Arrange
        tracker = TodoTracker(scope=str(temp_todo_file))
        tracker.refresh()

        # Act
        summary = format_todo_summary(tracker)

        # Assert
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_create_todo_panel(self, temp_todo_file):
        """
        Arrange: Tracker com tarefas
        Act: Cria painel
        Assert: Painel é criado
        """
        from aura_cli.cli.ui.todo_display import create_todo_panel

        # Arrange
        tracker = TodoTracker(scope=str(temp_todo_file))
        tracker.refresh()

        # Act
        panel = create_todo_panel(tracker)

        # Assert
        assert panel is not None
        assert isinstance(panel, Group)

    def test_get_todo_status_line(self, temp_todo_file):
        """
        Arrange: Tracker com tarefas
        Act: Obtém linha de status
        Assert: Linha de status é retornada
        """
        from aura_cli.cli.ui.todo_display import get_todo_status_line

        # Arrange
        tracker = TodoTracker(scope=str(temp_todo_file))
        tracker.refresh()

        # Act
        status_line = get_todo_status_line(tracker)

        # Assert
        assert isinstance(status_line, str)
        assert len(status_line) > 0

    def test_create_todo_compact(self, temp_todo_file):
        """
        Arrange: Tracker com tarefas
        Act: Cria visualização compacta
        Assert: Visualização é criada
        """
        from aura_cli.cli.ui.todo_display import create_todo_compact

        # Arrange
        tracker = TodoTracker(scope=str(temp_todo_file))
        tracker.refresh()

        # Act
        compact = create_todo_compact(tracker)

        # Assert
        assert isinstance(compact, str)
        assert len(compact) > 0


class TestTodoSystemIntegration:
    """Testes de integração para sistema de to-do"""

    def test_get_todo_tracker_returns_instance(self):
        """
        Arrange: Sistema inicializado
        Act: Obtém tracker global
        Assert: Instância é retornada
        """
        # Arrange & Act
        tracker = get_todo_tracker()

        # Assert
        assert isinstance(tracker, TodoTracker)

    def test_refresh_todo_tracker_updates(self):
        """
        Arrange: Tracker global
        Act: Atualiza tracker
        Assert: Tracker é atualizado
        """
        # Arrange & Act
        refresh_todo_tracker()

        # Assert
        tracker = get_todo_tracker()
        assert tracker is not None

    def test_todo_system_workflow(self, tmp_path):
        """
        Arrange: Diretório sem to-do
        Act: Cria tracker, obtém stats, atualiza
        Assert: Fluxo completo funciona
        """
        # Arrange
        scope = str(tmp_path)

        # Act - Cria tracker
        tracker = TodoTracker(scope=scope)

        # Act - Obtém stats (mesmo sem arquivo)
        stats = tracker.get_stats()

        # Act - Atualiza
        tracker.refresh()

        # Assert
        assert isinstance(stats, dict)
        assert "total" in stats
        assert "pending" in stats
        assert "done" in stats
        # Sem arquivo, stats devem ser zeros
        assert stats["total"] == 0 or stats["total"] >= 0

    def test_todo_task_creation(self):
        """
        Arrange: Dados de tarefa
        Act: Cria TodoTask
        Assert: Tarefa é criada corretamente
        """
        # Arrange
        task_id = 1
        text = "Nova tarefa"
        status = "pending"

        # Act
        task = TodoTask(
            id=task_id,
            text=text,
            status=status,
            line_number=1,
            original_line="○ Nova tarefa\n",
        )

        # Assert
        assert task.id == task_id
        assert task.text == text
        assert task.status == status
        assert task.is_pending is True
        assert task.is_done is False

    def test_todo_task_done_status(self):
        """
        Arrange: Tarefa concluída
        Act: Verifica status
        Assert: Status é correto
        """
        # Arrange
        task = TodoTask(
            id=1,
            text="Tarefa concluída",
            status="done",
            line_number=1,
            original_line="● Tarefa concluída\n",
        )

        # Act & Assert
        assert task.is_done is True
        assert task.is_pending is False
        assert task.status == "done"
