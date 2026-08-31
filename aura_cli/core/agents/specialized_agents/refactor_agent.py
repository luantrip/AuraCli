"""Refactoring specialised agent — inherits AgentBase.

Handles: plan_refactoring (impact + dependency analysis), analyze_impact,
apply_refactoring (safe execution with checkpoints), suggest_strategy.
Uses the full refactoring system from core.refactoring.
"""

from typing import Any, Dict, List, Optional

from aura_cli.core.agents.agent_base import AgentBase, AgentTask
from aura_cli.core.agents.specialized_agents._tool_schema import schemas_for_categories
from aura_cli.core.logger import get_logger
from aura_cli.core.service_registry import ToolCategory

logger = get_logger(__name__)


class RefactorAgent(AgentBase):
    """Specialised refactoring agent."""

    def __init__(self, agent_id: str = "refactor_agent", model: Optional[str] = None):
        """Initialise the RefactorAgent."""
        super().__init__(
            agent_id=agent_id,
            name="Refactor Agent",
            description="Agente especializado em refatoração de código",
            model=model,
        )

    def _execute_task(self, task: AgentTask) -> Any:
        """Execute a refactoring task."""
        task_type = task.parameters.get("type", "unknown")

        if task_type == "plan_refactoring":
            return self._handle_plan_refactoring(task)
        elif task_type == "analyze_impact":
            return self._handle_analyze_impact(task)
        elif task_type == "apply_refactoring":
            return self._handle_apply_refactoring(task)
        elif task_type == "suggest_strategy":
            return self._handle_suggest_strategy(task)
        else:
            raise ValueError(f"Tipo de tarefa desconhecido: {task_type}")

    def _handle_plan_refactoring(self, task: AgentTask) -> Any:
        """Handle a plan_refactoring request."""
        from aura_cli.core.refactoring.refactoring_planner import plan_refactoring

        pattern = task.parameters.get("pattern")
        replacement = task.parameters.get("replacement")
        scope = task.parameters.get("scope", ".")
        strategy = task.parameters.get("strategy", "incremental")

        if not all([pattern, replacement]):
            raise ValueError("Parâmetros 'pattern' e 'replacement' são obrigatórios")

        return str(
            plan_refactoring(
                str(pattern) if pattern else "",
                str(replacement) if replacement else "",
                scope,
                strategy,
            )
        )

    def _handle_analyze_impact(self, task: AgentTask) -> Any:
        """Handle an analyze_impact request."""
        from aura_cli.core.refactoring.refactoring_planner import (
            analyze_impact_for_refactoring,
        )

        file_path = task.parameters.get("file_path")
        action = task.parameters.get("action", "modify")
        scope = task.parameters.get("scope", ".")

        if not file_path:
            raise ValueError("Parâmetro 'file_path' é obrigatório")

        return analyze_impact_for_refactoring(file_path, action, scope)

    def _handle_apply_refactoring(self, task: AgentTask) -> str:
        """Handle an apply_refactoring request."""
        from aura_cli.core.refactoring.refactoring_executor import (
            apply_refactoring_plan,
        )

        plan = task.parameters.get("plan")
        if not plan:
            raise ValueError("Parâmetro 'plan' é obrigatório")

        return str(apply_refactoring_plan(plan))

    def _handle_suggest_strategy(self, task: AgentTask) -> str:
        """Handle a suggest_strategy request."""
        from aura_cli.core.refactoring.refactoring_planner import suggest_strategy

        pattern = task.parameters.get("pattern")
        scope = task.parameters.get("scope", ".")

        if not pattern:
            raise ValueError("Parâmetro 'pattern' é obrigatório")

        return str(suggest_strategy(pattern, scope))

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Return tool schemas for RefactorAgent derived from the ServiceRegistry.

        Categories exposed:
        - refactoring: plan_refactoring, analyze_impact, apply_refactoring, suggest_strategy
        - file_system: read_file, write_file, list_directory (needed to apply changes)
        - development: analyze_code, find_in_files (needed for impact analysis)
        """
        return schemas_for_categories(
            [
                ToolCategory.REFACTORING,
                ToolCategory.FILE_SYSTEM,
                ToolCategory.DEVELOPMENT,
            ],
            exclude_names=["browse_content", "web_search"],
        )
