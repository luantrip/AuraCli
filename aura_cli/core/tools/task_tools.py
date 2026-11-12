"""Task management tools for Aura CLI.

Provides create_task_list, complete_task, view_tasks, add_task,
get_next_task and start_autonomous_mode so the LLM agent can organise
and track complex multi-step work through function calling.
"""

from typing import List, Optional

from rich import print as rprint

from aura_cli.core.logger import get_logger
from aura_cli.core.todo.todo_tracker import get_todo_tracker
from aura_cli.core.ui import display_tool_call
from aura_cli.core.ui_bridge import UIIcons, UIStyles

logger = get_logger(__name__)


def create_task_list(tasks: List[str], objective: str = "") -> str:
    """Create a task list for a complex objective and save it to .aura/to-do.md.

    Args:
        tasks: List of strings — each string is one task.
               MUST be a list, not a single string or newline-separated text.
               Max 100 tasks.
        objective: Optional title describing the overall goal.

    Returns confirmation string with task IDs, or an error message if tasks
    is not a list.
    """
    MAX_TASKS = 100
    if isinstance(tasks, str):
        error_msg = (
            f"ERROR: 'tasks' must be a LIST of strings, not a single string.\n"
            f"Recebido: tipo string com {len(tasks)} caracteres.\n"
            f'Exemplo correto: ["Tarefa 1", "Tarefa 2", "Tarefa 3"]'
        )
        logger.error(error_msg)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{UIIcons.ERROR} {error_msg}[/{error_style}]")
        return error_msg
    if not isinstance(tasks, list):
        error_msg = (
            f"ERRO: 'tasks' deve ser uma lista, recebido: {type(tasks).__name__}"
        )
        logger.error(error_msg)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{UIIcons.ERROR} {error_msg}[/{error_style}]")
        return error_msg
    valid_tasks = []
    for i, task in enumerate(tasks):
        if isinstance(task, str):
            task = task.strip()
            if task and len(task) > 0:
                valid_tasks.append(task)
        else:
            logger.warning(
                f"Task {i} skipped: not a string (type: {type(task).__name__})"
            )

    if not valid_tasks:
        error_msg = "ERROR: No valid tasks found. Provide a list of non-empty strings."
        logger.error(error_msg)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{UIIcons.ERROR} {error_msg}[/{error_style}]")
        return error_msg
    if len(valid_tasks) > MAX_TASKS:
        warning_msg = (
            f"AVISO: Limitando a {MAX_TASKS} tarefas (recebidas {len(valid_tasks)})"
        )
        logger.warning(warning_msg)
        valid_tasks = valid_tasks[:MAX_TASKS]

    display_tool_call(
        "create_task_list", {"tasks": len(valid_tasks), "objective": objective}
    )

    try:
        tracker = get_todo_tracker()
        agi_tasks = []
        for i, task_text in enumerate(valid_tasks):
            agi_tasks.append(
                {"id": f"task_{i + 1}", "description": task_text, "type": "automated"}
            )
        tracker.add_agi_plan(
            plan_description=objective or "Tarefas automatizadas", tasks=agi_tasks
        )
        output = [
            f"{UIIcons.SUCCESS} Lista de tarefas criada!",
            "",
            f"📋 Objetivo: {objective or 'Tarefas automatizadas'}",
            f"📊 Total: {len(valid_tasks)} tarefas",
            "",
            "Tarefas criadas:",
        ]
        for i, task_text in enumerate(valid_tasks[:20]):
            output.append(f"  {i + 1}. [ ] {task_text}")

        if len(valid_tasks) > 20:
            output.append(f"  ... e mais {len(valid_tasks) - 20} tarefas")

        output.append("")
        output.append("Use 'complete_task' to mark tasks as completed.")
        output.append("Use 'get_next_task' to see the next pending task.")

        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(
            f"[{success_style}]{UIIcons.SUCCESS} {len(valid_tasks)} tarefas criadas[/{success_style}]"
        )

        return "\n".join(output)

    except Exception as e:
        error_msg = f"Error creating task list: {e}"
        logger.error(error_msg, exc_info=True)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def complete_task(
    task_id: Optional[int] = None, task_text: Optional[str] = None
) -> str:
    """Mark a task as done by ID or partial text match.

    Args:
        task_id: Zero-based numeric task ID. Optional if task_text provided.
        task_text: Partial task description for lookup. Optional if task_id provided.

    Returns:
        Confirmation string with progress and next task, or an error message.
    """
    display_tool_call("complete_task", {"task_id": task_id, "task_text": task_text})

    try:
        tracker = get_todo_tracker()

        if task_id is not None:
            success, completed_text = tracker.mark_task_done(task_id)
        elif task_text:
            success, completed_text = tracker.mark_task_by_text(task_text)
        else:
            return "Error: Provide task_id or task_text to identify the task."

        if success:
            stats = tracker.get_stats()
            progress = f"{stats['done']}/{stats['total']}"

            output = f"{UIIcons.SUCCESS} Task completed: {completed_text}\n"
            output += f"📊 Progresso: {progress} tarefas completadas"
            next_task = tracker.get_current_task()
            if next_task:
                output += f"\n⏭️  Next: {next_task.text}"
            else:
                output += "\n🎉 All tasks completed!"

            success_style = UIStyles.safe_style("SUCCESS", "green")
            rprint(
                f"[{success_style}]{UIIcons.SUCCESS} Tarefa completada[/{success_style}]"
            )

            return output
        else:
            return "Could not complete the task. Check that the ID/text is correct."

    except Exception as e:
        error_msg = f"Error completing task: {e}"
        logger.error(error_msg, exc_info=True)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def view_tasks() -> str:
    """Return a formatted overview of all tasks and their statuses.

    Returns:
        Multi-line string with pending and completed tasks, progress
        statistics and the next pending task.
    """
    display_tool_call("view_tasks", {})

    try:
        tracker = get_todo_tracker()
        all_tasks = tracker.get_all_tasks()
        stats = tracker.get_stats()

        if not all_tasks:
            return "📋 No tasks registered. Use 'create_task_list' to create tasks."

        output = [
            "📋 Lista de Tarefas",
            "═══════════════════════════════════════",
            f"📊 Progresso: {stats['done']}/{stats['total']} ({(stats['done'] / stats['total'] * 100):.0f}%)"
            if stats["total"] > 0
            else "",
            "",
        ]
        pending = tracker.get_pending_tasks()
        if pending:
            output.append("📌 Pendentes:")
            for task in pending:
                output.append(f"  {task.id}. [ ] {task.text}")
            output.append("")
        done = tracker.get_done_tasks()
        if done:
            output.append("✅ Completed:")
            for task in done:
                output.append(f"  {task.id}. [x] {task.text}")
        current = tracker.get_current_task()
        if current:
            output.append("")
            output.append(f"⏭️  Next task: {current.text}")

        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(
            f"[{success_style}]{UIIcons.SUCCESS} {len(all_tasks)} tarefas listadas[/{success_style}]"
        )

        return "\n".join(output)

    except Exception as e:
        error_msg = f"Error listing tasks: {e}"
        logger.error(error_msg, exc_info=True)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def add_task(task_text: str) -> str:
    """Add a new task to the existing list.

    Use for tasks discovered during plan execution.

    Args:
        task_text: Description of the task to add.

    Returns:
        Confirmation string with updated total count.
    """
    display_tool_call("add_task", {"task_text": task_text})

    try:
        tracker = get_todo_tracker()
        success = tracker.add_task(task_text)

        if success:
            stats = tracker.get_stats()
            output = f"{UIIcons.SUCCESS} Tarefa adicionada: {task_text}\n"
            output += f"📊 Total de tarefas: {stats['total']}"

            success_style = UIStyles.safe_style("SUCCESS", "green")
            rprint(
                f"[{success_style}]{UIIcons.SUCCESS} Tarefa adicionada[/{success_style}]"
            )

            return output
        else:
            return "Error adding task."

    except Exception as e:
        error_msg = f"Error adding task: {e}"
        logger.error(error_msg, exc_info=True)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def get_next_task() -> str:
    """Return the next pending task for execution.

    Returns:
        Task description with ID and progress statistics, or a
        completion message if no tasks remain.
    """
    display_tool_call("get_next_task", {})

    try:
        tracker = get_todo_tracker()
        current = tracker.get_current_task()

        if current:
            stats = tracker.get_stats()
            output = f"⏭️  Next task (ID: {current.id}):\n"
            output += f"   {current.text}\n"
            output += (
                f"📊 Progress: {stats['done']}/{stats['total']} tasks completed"
            )

            success_style = UIStyles.safe_style("SUCCESS", "green")
            rprint(
                f"[{success_style}]{UIIcons.SUCCESS} Tarefa pendente encontrada[/{success_style}]"
            )

            return output
        else:
            return "🎉 All tasks completed! No pending tasks."

    except Exception as e:
        error_msg = f"Error fetching next task: {e}"
        logger.error(error_msg, exc_info=True)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def start_autonomous_mode() -> str:
    """Activate autonomous task execution mode.

    Prints instructions directing the agent to execute the current task,
    mark it complete with complete_task(), then call get_next_task() and
    repeat until all tasks are done. Use when the user asks for autonomous
    or automatic execution.

    Returns:
        Detailed instructions with the current task and progress summary.
    """
    display_tool_call("start_autonomous_mode", {})

    try:
        tracker = get_todo_tracker()
        current = tracker.get_current_task()
        stats = tracker.get_stats()

        if not current:
            if stats["total"] == 0:
                return (
                    "❌ No task list found.\n\n"
                    "To use autonomous mode, first create a task list with:\n"
                    "create_task_list(tasks=[...], objective='...')"
                )
            else:
                return "🎉 All tasks are already completed!"

        pending = stats["total"] - stats["done"]

        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(
            f"[{success_style}]{UIIcons.SUCCESS} Autonomous mode activated[/{success_style}]"
        )

        output = f"""
🤖 AUTONOMOUS MODE ACTIVATED
{"=" * 50}

📊 Status: {stats["done"]}/{stats["total"]} tasks completed ({pending} pending)

📋 TAREFA ATUAL (ID: {current.id}):
   {current.text}

⚡ AUTOMATION INSTRUCTIONS:
   1. Execute this task using the available tools
   2. After completing, call: complete_task(task_id={current.id})
   3. Em seguida, chame: get_next_task() para continuar
   4. Repeat until all tasks are completed

💡 DICAS:
   - Use read_file, write_file, edit_file para arquivos
   - Use run_shell_command para comandos do sistema
   - Use list_directory, tree_view para explorar estrutura
   - Be proactive and execute without asking for confirmation

🚀 Comece agora executando a tarefa acima!
"""
        return output

    except Exception as e:
        error_msg = f"Error starting autonomous mode: {e}"
        logger.error(error_msg, exc_info=True)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg


def get_automation_status() -> str:
    """Return a detailed progress report for the current task automation.

    Returns:
        Status report with progress bar, counts and next pending task.
    """
    display_tool_call("get_automation_status", {})

    try:
        tracker = get_todo_tracker()
        stats = tracker.get_stats()
        all_tasks = tracker.get_all_tasks()

        if not all_tasks:
            return "📋 No tasks registered."

        pending = tracker.get_pending_tasks()
        done = tracker.get_done_tasks()
        percent = (stats["done"] / stats["total"] * 100) if stats["total"] > 0 else 0
        bar_length = 20
        filled = int(bar_length * percent / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        output = f"""
📊 AUTOMATION STATUS
{"=" * 50}

Progresso: [{bar}] {percent:.0f}%
Tasks: {stats["done"]}/{stats["total"]} completed

"""

        if done:
            output += "✅ COMPLETED:\n"
            for task in done[-5:]:  # Last 5 completed
                output += (
                    f"   • {task.text[:60]}{'...' if len(task.text) > 60 else ''}\n"
                )
            if len(done) > 5:
                output += f"   ... e mais {len(done) - 5} tarefas\n"
            output += "\n"

        if pending:
            output += "📌 PENDENTES:\n"
            for task in pending[:5]:  # Next 5 pending
                output += f"   • [{task.id}] {task.text[:60]}{'...' if len(task.text) > 60 else ''}\n"
            if len(pending) > 5:
                output += f"   ... e mais {len(pending) - 5} tarefas\n"
            output += f"\n⏭️  Next: {pending[0].text}\n"
        else:
            output += "🎉 ALL TASKS COMPLETED!\n"

        success_style = UIStyles.safe_style("SUCCESS", "green")
        rprint(f"[{success_style}]{UIIcons.SUCCESS} Status obtido[/{success_style}]")

        return output

    except Exception as e:
        error_msg = f"Error fetching status: {e}"
        logger.error(error_msg, exc_info=True)
        error_style = UIStyles.safe_style("ERROR", "red")
        rprint(f"[{error_style}]{error_msg}[/{error_style}]")
        return error_msg
