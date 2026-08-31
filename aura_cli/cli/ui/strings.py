"""UI Strings - Centralized UI text constants.

Provides centralized UI strings for consistency and future i18n support.
All user-facing strings should be defined here instead of hardcoded.

Categories:
    - Actions: User actions (expand, collapse, etc.)
    - Status: Status messages (completed, pending, etc.)
    - Labels: UI labels and headers
    - Messages: User feedback messages

Future: This module will be the foundation for i18n/l10n support.
"""


class UIStrings:
    """Centralized UI strings for consistency."""

    # Actions
    EXPAND = "expandir"
    COLLAPSE = "recolher"
    CLICK_TO_EXPAND = "clique para expandir"

    # Status
    COMPLETED = "concluídas"
    COMPLETED_SINGULAR = "concluída"
    PENDING = "pendentes"
    WORKING_ON = "Trabalhando em"
    ALL_DONE = "Tudo concluído"
    CANCELLED = "cancelada"
    TASK_COMPLETED = "Tarefa concluída"
    PROGRESS = "Progresso"
    CURRENT = "atual"

    # Labels
    TASKS = "tarefas"
    LINES = "linhas"
    LINES_OMITTED = "linhas omitidas"
    MORE_LINES = "mais linhas"
    CHARACTERS = "caracteres"

    # Messages
    COMMANDS_AVAILABLE = "Comandos Disponíveis"

    @staticmethod
    def expand_hint(remaining: int, unit: str = "linhas") -> str:
        """Format expand hint message.

        Args:
            remaining: Number of remaining items
            unit: Unit name (linhas, caracteres, etc.)

        Returns:
            Formatted hint string
        """
        return f"⋯ {remaining} {unit}  [e] {UIStrings.EXPAND}"

    @staticmethod
    def omitted_hint(count: int) -> str:
        """Format omitted content hint.

        Args:
            count: Number of omitted items

        Returns:
            Formatted hint string
        """
        return f"... {count} {UIStrings.LINES_OMITTED} ..."

    @staticmethod
    def tasks_completed(count: int) -> str:
        """Format tasks completed message.

        Args:
            count: Number of completed tasks

        Returns:
            Formatted message
        """
        unit = UIStrings.COMPLETED_SINGULAR if count == 1 else UIStrings.COMPLETED
        return f"{count} {unit}"

    @staticmethod
    def working_on_tasks(count: int) -> str:
        """Format working on tasks message.

        Args:
            count: Number of tasks being worked on

        Returns:
            Formatted message
        """
        return f"{UIStrings.WORKING_ON} {count} {UIStrings.TASKS}"

    @staticmethod
    def tasks_pending(count: int) -> str:
        """Format the number of pending tasks."""
        return f"{count} {UIStrings.PENDING}"
