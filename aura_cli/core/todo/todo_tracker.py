"""Task tracking system backed by .aura/to-do.md.

Parses multiple markdown checklist formats (- [ ], ☐, o for pending;
- [x], ☒, * for done). Uses mtime-based cache to avoid unnecessary reads.
Global singleton accessible via get_todo_tracker() / refresh_todo_tracker().
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar, Dict, List, Optional, Tuple

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class TodoTask:
    """A single to-do task (id, text, status: pending/working/done)."""

    id: int
    text: str
    status: str  # "pending" ou "done"
    line_number: int
    original_line: str

    @property
    def is_done(self) -> bool:
        """Check if done."""
        return self.status == "done"

    @property
    def is_pending(self) -> bool:
        """Check if pending."""
        return self.status == "pending"


class TodoTracker:
    """Tracker de tarefas do arquivo to-do.md"""

    PENDING_SYMBOLS: ClassVar[list] = ["o", "☐", "- [ ]"]
    DONE_SYMBOLS: ClassVar[list] = ["*", "☒", "- [x]", "- [X]"]

    def __init__(self, scope: str = "."):
        """
        Initialise the task tracker

        Args:
            scope: Project root directory
        """
        self.scope = Path(scope).resolve()
        from aura_cli.core.paths import ArtifactLayout

        self.todo_file = ArtifactLayout(self.scope).project("to-do.md")
        self.tasks: List[TodoTask] = []
        self.last_modified: Optional[datetime] = None
        self._load_tasks()

    def _load_tasks(self) -> bool:
        """Load tasks from to-do.md, parsing [ ], [x] and [>] markers."""
        if not self.todo_file.exists():
            logger.debug(f"to-do.md file not found: {self.todo_file}")
            return False

        try:
            mtime = datetime.fromtimestamp(self.todo_file.stat().st_mtime)
            if self.last_modified and mtime <= self.last_modified:
                return True

            self.last_modified = mtime

            with open(self.todo_file, encoding="utf-8") as f:
                lines = f.readlines()

            self.tasks = []
            task_id = 0

            for line_num, line in enumerate(lines, 1):
                task = self._parse_task_line(line, line_num, task_id)
                if task:
                    self.tasks.append(task)
                    task_id += 1

            logger.info(f"Loaded {len(self.tasks)} tasks from to-do.md")
            return True

        except FileNotFoundError:
            logger.debug(f"to-do.md file not found: {self.todo_file}")
            return False
        except PermissionError as e:
            logger.error(
                f"Erro de permissão ao ler arquivo to-do.md: {self.todo_file}. "
                f"Verifique se você tem permissão de leitura. Erro: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Erro inesperado ao carregar tarefas do arquivo {self.todo_file}: {e}. "
                f"Tipo de erro: {type(e).__name__}. "
                "Verifique se o arquivo está acessível e tem formato válido."
            )
            return False

    def _parse_task_line(
        self, line: str, line_number: int, task_id: int
    ) -> Optional[TodoTask]:
        """Parse a task line from the Markdown file. Returns TodoTask or None."""
        line_stripped = line.strip()

        is_pending = False
        is_done = False

        for symbol in self.PENDING_SYMBOLS:
            if line_stripped.startswith(symbol):
                is_pending = True
                break

        for symbol in self.DONE_SYMBOLS:
            if line_stripped.startswith(symbol):
                is_done = True
                break

        if not (is_pending or is_done):
            return None

        text = line_stripped
        for symbol in self.PENDING_SYMBOLS + self.DONE_SYMBOLS:
            if text.startswith(symbol):
                text = text[len(symbol) :].strip()
                break

        status = "done" if is_done else "pending"

        return TodoTask(
            id=task_id,
            text=text,
            status=status,
            line_number=line_number,
            original_line=line,
        )

    def refresh(self) -> bool:
        """Reload tasks from the file."""
        return self._load_tasks()

    def get_stats(self) -> Dict[str, int]:
        """Return task counts: total, pending, working, done."""
        self.refresh()  # Atualiza antes de calcular

        total = len(self.tasks)
        pending = sum(1 for t in self.tasks if t.is_pending)
        done = sum(1 for t in self.tasks if t.is_done)
        working = 1 if pending > 0 else 0  # Assume 1 task in progress

        return {"total": total, "pending": pending, "done": done, "working": working}

    def get_pending_tasks(self) -> List[TodoTask]:
        """Return all pending tasks."""
        self.refresh()
        return [t for t in self.tasks if t.is_pending]

    def get_done_tasks(self) -> List[TodoTask]:
        """Return all completed tasks."""
        self.refresh()
        return [t for t in self.tasks if t.is_done]

    def get_current_task(self) -> Optional[TodoTask]:
        """Return the current working task, or None."""
        pending = self.get_pending_tasks()
        return pending[0] if pending else None

    def get_all_tasks(self) -> List[TodoTask]:
        """Return all tasks."""
        self.refresh()
        return self.tasks.copy()

    def mark_task_done(
        self, task_id: int, notify: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """Mark a task done by ID. Returns (success, task_text)."""
        if not self.todo_file.exists():
            return False, None

        try:
            task = next((t for t in self.tasks if t.id == task_id), None)
            if not task or task.is_done:
                return False, None

            task_text = task.text

            with open(self.todo_file, encoding="utf-8") as f:
                lines = f.readlines()

            line = lines[task.line_number - 1]

            new_line = line
            for symbol in self.PENDING_SYMBOLS:
                if line.strip().startswith(symbol):
                    new_line = line.replace(symbol, "*", 1)
                    break

            lines[task.line_number - 1] = new_line

            with open(self.todo_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

            # The filesystem mtime may have coarse resolution; force a reload
            # so stats and subsequent consumers observe the new status.
            self.last_modified = None
            self.refresh()
            logger.info(f"Task {task_id} marked as completed: {task_text}")
            return True, task_text if notify else None

        except FileNotFoundError:
            logger.error(
                f"to-do.md file not found: {self.todo_file}. "
                f"Não é possível marcar tarefa {task_id} como concluída."
            )
            return False, None
        except PermissionError as e:
            logger.error(
                f"Erro de permissão ao escrever no arquivo to-do.md: {self.todo_file}. "
                f"Não é possível marcar tarefa {task_id} como concluída. "
                f"Verifique permissões de escrita. Erro: {e}"
            )
            return False, None
        except IndexError as e:
            logger.error(
                f"Error: Task {task_id} has invalid line number ({task.line_number if task else 'N/A'}). "
                f"O arquivo pode ter sido modificado. Tente recarregar com refresh(). Erro: {e}"
            )
            return False, None
        except Exception as e:
            logger.error(
                f"Erro inesperado ao marcar tarefa {task_id} como concluída no arquivo {self.todo_file}: {e}. "
                f"Tipo de erro: {type(e).__name__}. "
                "Verifique se o arquivo está acessível e não está corrompido."
            )
            return False, None

    def add_task(self, text: str, position: Optional[int] = None) -> bool:
        """Append a new task to the list. Returns True on success."""
        if not self.todo_file.exists():
            self.todo_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.todo_file, "w", encoding="utf-8") as f:
                f.write("# Lista de Tarefas\n\n")

        try:
            with open(self.todo_file, encoding="utf-8") as f:
                lines = f.readlines()

            new_line = f"o {text}\n"

            if position is None:
                lines.append(new_line)
            else:
                lines.insert(position, new_line)

            with open(self.todo_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

            self.refresh()
            logger.info(f"New task added: {text}")
            return True

        except PermissionError as e:
            logger.error(
                f"Erro de permissão ao escrever no arquivo to-do.md: {self.todo_file}. "
                f"Não é possível adicionar tarefa '{text}'. "
                f"Verifique permissões de escrita. Erro: {e}"
            )
            return False
        except OSError as e:
            logger.error(
                f"Erro de sistema ao escrever no arquivo to-do.md: {self.todo_file}. "
                f"Não é possível adicionar tarefa '{text}'. "
                f"Verifique se há espaço em disco e se o diretório existe. Erro: {e}"
            )
            return False
        except Exception as e:
            logger.error(
                f"Erro inesperado ao adicionar tarefa '{text}' no arquivo {self.todo_file}: {e}. "
                f"Tipo de erro: {type(e).__name__}. "
                "Verifique se o arquivo está acessível."
            )
            return False

    def add_agi_plan(
        self, plan_description: str, tasks: List[Dict[str, Any]]
    ) -> List[int]:
        """Add a complete AGI plan to to-do.md.

        Syncs AGI Worker tasks with the persistence layer so progress
        can be tracked across sessions.

        Args:
            plan_description: High-level description of the plan.
            tasks: List of dicts with keys id, description, type and
                (optionally) dependencies.

        Returns:
            List of task IDs created in TodoTracker.
        """
        created_ids = []

        if not self.todo_file.exists():
            self.todo_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.todo_file, "w", encoding="utf-8") as f:
                f.write("# Lista de Tarefas\n\n")

        try:
            with open(self.todo_file, encoding="utf-8") as f:
                lines = f.readlines()

            lines.append(f"\n## 🤖 AGI Plan: {plan_description}\n")

            for task in tasks:
                task_desc = task.get("description", f"Task {task.get('id', 'unknown')}")
                task_type = task.get("type", "")

                task_text = f"[{task_type}] {task_desc}" if task_type else task_desc

                lines.append(f"o {task_text}\n")

            with open(self.todo_file, "w", encoding="utf-8") as f:
                f.writelines(lines)

            self.refresh()

            all_tasks = self.get_all_tasks()
            if len(all_tasks) >= len(tasks):
                created_ids = [t.id for t in all_tasks[-len(tasks) :]]

            logger.info(f"AGI Plan added: {len(tasks)} tasks created")
            return created_ids

        except Exception as e:
            logger.error(f"Error adding AGI plan: {e}")
            return []

    def mark_task_by_text(self, text_pattern: str) -> Tuple[bool, Optional[str]]:
        """Mark a task done by partial text match. Returns (success, task_text)."""
        self.refresh()

        for task in self.tasks:
            if task.is_pending and text_pattern.lower() in task.text.lower():
                return self.mark_task_done(task.id)

        logger.warning(f"No pending tasks found matching pattern: {text_pattern}")
        return False, None

    def get_agi_plan_tasks(self) -> List[TodoTask]:
        """Return AGI plan tasks."""
        self.refresh()
        import re

        agi_tasks = []
        for task in self.tasks:
            if re.match(r"^\[[\w_]+\]", task.text):
                agi_tasks.append(task)

        return agi_tasks


_global_tracker: Optional[TodoTracker] = None


def get_todo_tracker(scope: str = ".") -> TodoTracker:
    """Return the TodoTracker singleton."""
    # Try DI container first (preferred path)
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.TODO_TRACKER):
            return container.resolve(Services.TODO_TRACKER)
    except Exception:
        pass

    # Fallback to legacy singleton
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TodoTracker(scope=scope)
    return _global_tracker


def refresh_todo_tracker(scope: str = ".") -> TodoTracker:
    """Force a tracker refresh and return a new singleton."""
    global _global_tracker
    _global_tracker = TodoTracker(scope=scope)
    return _global_tracker
