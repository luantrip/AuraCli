"""
AgiPlanner Module.

This module encapsulates the planning and decision-making logic for the AGI system.
It is responsible for:
- Decomposing high-level user requests into actionable tasks.
- Using LLMs to generate structured execution plans.
- Syncing plans with the TodoTracker.
- managing plan confirmation and tool execution safety checks.
"""

import json
import logging
from typing import Any, Dict, List, Optional
import uuid

from aura_cli.core.exceptions import LLMError
from aura_cli.core.ui_bridge import UIIcons

try:
    from aura_cli.core.tools.human_intervention_adapter import (
        HumanInterventionAdapter,
        InterventionHelper,
    )
except ImportError:
    HumanInterventionAdapter = None  # type: ignore[assignment,misc]
    InterventionHelper = None  # type: ignore[assignment,misc]
from aura_cli.core.agi.stage_ledger import StageLedger
from aura_cli.core.events.human_intervention_events import (
    InterventionContext,
    RiskLevel,
)
from aura_cli.core.llm.base import query_with_fallback

logger = logging.getLogger(__name__)


def _normalize_subtask_params(params: dict) -> dict:
    """Ensure required parameters are present for known task types."""
    task_type = params.get("type", "unknown")
    if task_type in {
        "analyze_code",
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "tree_view",
    }:
        params.setdefault("path", ".")
        if task_type == "analyze_code":
            params.setdefault("file_path", params["path"])
    if task_type == "find_in_files":
        params.setdefault("path", ".")
        params.setdefault("pattern", "")
    if task_type == "write_file":
        params.setdefault("content", "")
    params.setdefault("type", task_type)
    return params


class AgiPlanner:
    """
    Handles planning, decomposition, and safety checks for AGI tasks.
    """

    def __init__(
        self,
        model: str,
        project_root: Any,
        agi_event_adapter: Any,
        human_intervention_adapter: HumanInterventionAdapter,
        task_planner: Any = None,
        problem_decomposer: Any = None,
        use_advanced_features: bool = True,
        allowed_task_types: Optional[List[str]] = None,
    ):
        """Initialize the instance."""
        self.model = model
        self.project_root = project_root
        self.agi_event_adapter = agi_event_adapter
        self.human_intervention_adapter = human_intervention_adapter
        self.task_planner = task_planner
        self.problem_decomposer = problem_decomposer
        self.use_advanced_features = use_advanced_features
        self.allowed_task_types = allowed_task_types or [
            "analyze_project_structure",
            "analyze_project_quality",
            "analyze_project_security",
            "analyze_project_documentation",
            "compare_project_fronts",
            "read_file",
            "write_file",
            "list_directory",
            "codebase_search",
            "investigate_codebase",
            "analyze_code",
            "analyze_code_nlp",
            "review_file",
            "validate_syntax",
            "edit_file",
            "tree_view",
            "find_in_files",
            "run_tests",
            "find_related_tests",
            "validate_tests_pass",
            "generate_tests",
            "plan_refactoring",
            "analyze_impact",
            "apply_refactoring",
            "suggest_strategy",
        ]
        self.stage_ledger = StageLedger(f"agi-{uuid.uuid4().hex[:12]}")

    def plan_with_llm(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Uses LLM to create a structured task plan based on the prompt.

        Returns:
            List of tasks with all necessary parameters or None
        """
        try:
            default_prompt = """Você é um planejador de tasks especializado. Analise o pedido do usuário e crie um plano estruturado de tasks.

**IMPORTANTE**: Se o pedido do usuário for muito vago ou não tiver contexto suficiente (ex: "faz algo", "melhore", "analise este projeto"), você DEVE começar com tasks exploratórias para entender o contexto antes de criar tasks específicas.

**ESTRATÉGIA DE ANÁLISE DE PROJETOS:**
Quando o usuário pedir para analisar um projeto, entender código, ou explorar um codebase:
1. PRIMEIRO: Use 'analyze_project_structure' para obter visão geral completa
2. DEPOIS: Leia READMEs principais (root e frentes identificadas)
3. ENTÃO: Explore estrutura com 'list_directory' se necessário
4. DEPOIS: Use ferramentas de insights de projeto para análises profundas:
   - 'analyze_project_quality' para qualidade de código
   - 'analyze_project_security' para segurança
   - 'analyze_project_documentation' para documentação
   - 'compare_project_fronts' para comparar frentes (backend, frontend, mobile, etc.)
5. FINALMENTE: Use ferramentas específicas para análise/edição/refatoração/testes quando necessário

**FERRAMENTAS DISPONÍVEIS:**
- 'analyze_project_structure': Análise estruturada completa de projetos (USE PRIMEIRO para projetos)
- 'analyze_project_quality': Avaliação de qualidade de código em nível de projeto
- 'analyze_project_security': Análise de segurança e dependências vulneráveis
- 'analyze_project_documentation': Avaliação de documentação (READMEs, docstrings)
- 'compare_project_fronts': Comparação entre diferentes frentes do projeto
- 'list_directory': Lista conteúdo de diretórios (para explorar estrutura)
- 'read_file': Lê arquivos específicos (README, configs, código)
- 'codebase_search': Busca texto/padrões no código
- 'investigate_codebase': Análise profunda com AST
- 'analyze_code': Análise de ARQUIVO específico (não diretório)
- 'analyze_code_nlp': Análise NLP de ARQUIVO específico (não diretório)
- 'review_file': Revisão completa de arquivo com análise aprofundada
- 'run_tests': Executa testes em um caminho ou suite
- 'find_related_tests': Descobre testes relacionados a um arquivo
- 'validate_tests_pass': Verifica se uma suite está passando
- 'generate_tests': Gera testes para um arquivo específico
- 'plan_refactoring': Planeja uma refatoração estruturada
- 'analyze_impact': Analisa impacto de uma mudança
- 'apply_refactoring': Aplica plano de refatoração
- 'suggest_strategy': Sugere estratégia de refatoração

**FORMATO DE RESPOSTA (JSON):**
{
  "tasks": [
    {
      "id": "tarefa_1",
      "description": "Descrição clara da tarefa",
      "type": "analyze_project_structure|analyze_project_quality|analyze_project_security|analyze_project_documentation|compare_project_fronts|read_file|write_file|list_directory|codebase_search|investigate_codebase|analyze_code|analyze_code_nlp|review_file|validate_syntax|edit_file|tree_view|find_in_files|run_tests|find_related_tests|validate_tests_pass|generate_tests|plan_refactoring|analyze_impact|apply_refactoring|suggest_strategy",
      "agent": "code_agent|review_agent|refactor_agent|test_agent",
      "priority": 5,
      "dependencies": [],
      "parameters": {
        "path": "caminho/do/arquivo",
        "content": "conteúdo se for write_file",
        "pattern": "padrão se for find_in_files",
        ...
      }
    }
  ]
}

**REGRAS OBRIGATÓRIAS:**
1. Cada tarefa DEVE ter TODOS os parâmetros necessários
2. Para read_file, write_file, edit_file, list_directory, tree_view: SEMPRE inclua "path" (use "." se não especificado)
3. Para analyze_code:
   - Se agent="code_agent": use "path" (pode ser diretório ou arquivo)
   - Se agent="review_agent" ou "refactor_agent": use "file_path" (NÃO "path")
   - IMPORTANTE: analyze_code com review_agent/refactor_agent precisa de um ARQUIVO ESPECÍFICO, não um diretório!
   - Exemplo correto: {"file_path": "app.py"} ou {"file_path": "main.py"}
   - Exemplo ERRADO: {"file_path": "."} ou {"file_path": "templates/"}
4. Para find_in_files: inclua "pattern" e "path"
5. Para review_file, find_related_tests e generate_tests: inclua "file_path"
6. Para run_tests e validate_tests_pass: prefira incluir "test_path"
7. Para plan_refactoring: inclua "pattern" e "replacement"
8. Para analyze_impact: inclua "file_path"
9. Para apply_refactoring: inclua "plan"
10. Para suggest_strategy: inclua "pattern"
11. Dependências devem usar IDs de tasks anteriores
12. Seja específico com caminhos e parâmetros
13. SEMPRE comece com list_directory(".") para entender o projeto
14. Se o pedido for vago, crie tasks exploratórias primeiro
15. Para analyze_code: Se não souber qual arquivo, use list_directory primeiro e depois analyze_code com arquivo específico

**ESTRATÉGIA:**
- Pedido vago → Comece explorando (list_directory, tree_view)
- Pedido específico → Crie tasks diretas com parâmetros específicos
- Sempre inclua parâmetros, mesmo que sejam valores padrão

Retorne APENAS o JSON, sem markdown, sem explicações."""

            planning_prompt = system_prompt or default_prompt

            messages = [
                {"role": "system", "content": planning_prompt},
                {"role": "user", "content": f"Pedido do usuário: {prompt}"},
            ]

            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura AGI] {UIIcons.THINKING} Planejando tasks com LLM...",
            )

            raw_content = self._call_planning_llm(messages)
            if raw_content is None:
                return None
            return self._parse_plan_response(raw_content)

        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Erro de conexão ao planejar com LLM: {e}", exc_info=True)
            raise LLMError(  # type: ignore[call-arg]
                f"Connection error during planning: {e}",
                model=self.model,
                original_error=e,
            ) from e
        except (ValueError, TypeError) as e:
            logger.error(f"Erro de validação ao planejar com LLM: {e}", exc_info=True)
            raise LLMError(  # type: ignore[call-arg]
                f"Validation error during planning: {e}",
                model=self.model,
                original_error=e,
            ) from e
        except Exception as e:
            logger.error(f"Unexpected error planning with LLM: {e}", exc_info=True)
            raise LLMError(  # type: ignore[call-arg]
                f"Unexpected error during planning: {e}",
                model=self.model,
                original_error=e,
            ) from e

    def _call_planning_llm(self, messages: list) -> Optional[str]:
        """Call LLM for planning and return raw content string, or None on failure."""
        response = query_with_fallback(
            model=self.model,
            messages=messages,
            max_retries=2,
            timeout=15.0,
        )
        if not response or not hasattr(response, "choices") or not response.choices:
            logger.warning("LLM não retornou resposta para planejamento")
            return None
        content = response.choices[0].message.content.strip()
        for prefix in ("```json", "```"):
            if content.startswith(prefix):
                content = content[len(prefix) :]
        if content.endswith("```"):
            content = content[:-3]
        return content.strip()

    def _parse_plan_response(self, content: str) -> Optional[List[Dict[str, Any]]]:
        """Parse and validate LLM plan JSON response into task list."""
        try:
            plan_data = json.loads(content)
            tasks = plan_data.get("tasks", [])
            if not tasks:
                logger.warning("LLM retornou plano sem tasks")
                return None

            from aura_cli.core.agents.planning.task_parameter_normalizer import (
                normalize_task_params,
            )

            validated_tasks = []
            for task in tasks:
                task_id = task.get("id") or str(uuid.uuid4())[:8]
                task_type = task.get("type", "").lower()
                if task_type not in self.allowed_task_types:
                    logger.warning(f"Invalid task type: {task_type}, skipping...")
                    continue
                params = task.get("parameters", {}).copy()
                agent_id = task.get("agent", "code_agent")
                normalized_params, norm_errors = normalize_task_params(
                    task_type=task_type,
                    params=params,
                    agent_id=agent_id,
                    working_directory=str(self.project_root)
                    if self.project_root
                    else None,
                )
                if norm_errors:
                    if "file_path must be a file" in str(norm_errors):
                        logger.warning(
                            f"Changing task {task_type} to list_directory: {norm_errors}"
                        )
                        task_type = "list_directory"
                        normalized_params, _ = normalize_task_params(
                            task_type="list_directory",
                            params={
                                "path": params.get("path", params.get("file_path", "."))
                            },
                        )
                    else:
                        logger.warning(
                            f"Normalização de parâmetros para {task_id}: {norm_errors}"
                        )
                validated_tasks.append(
                    {
                        "id": task_id,
                        "description": task.get("description", f"Tarefa {task_id}"),
                        "type": task_type,
                        "agent": task.get("agent", "code_agent"),
                        "priority": task.get("priority", 5),
                        "dependencies": task.get("dependencies", []),
                        "parameters": normalized_params,
                    }
                )

            if not validated_tasks:
                logger.warning("No valid tasks after validation")
                return None

            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura AGI] {UIIcons.SUCCESS} Plan created: {len(validated_tasks)} structured tasks",
            )
            return validated_tasks
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing planning JSON: {e}")
            logger.debug(f"Conteúdo recebido: {content[:200]}")
            return None

    def decompose_and_plan(
        self, prompt: str, system_prompt: Optional[str] = None
    ) -> Optional[Any]:
        """
        Decomposes the problem and creates an execution plan.
        Uses LLM first, with fallback to automatic decomposition.

        Returns:
            TaskPlan if successful, None otherwise
        """
        if not self.use_advanced_features or not self.task_planner:
            return None

        try:
            from aura_cli.core.agents.planning.task_planner import PlanStrategy

            llm_tasks = self.plan_with_llm(prompt, system_prompt)

            if llm_tasks:
                tasks_data = []
                task_id_map = {}

                for task in llm_tasks:
                    new_id = str(uuid.uuid4())[:8]
                    task_id_map[task["id"]] = new_id

                    dependencies = []
                    for dep_id in task.get("dependencies", []):
                        if dep_id in task_id_map:
                            dependencies.append(task_id_map[dep_id])

                    params = task.get("parameters", {})
                    params["type"] = task["type"]
                    params["agent"] = task.get("agent", "code_agent")

                    tasks_data.append(
                        {
                            "id": new_id,
                            "description": task["description"],
                            "priority": task.get("priority", 5),
                            "dependencies": dependencies,
                            "parameters": params,
                        }
                    )

                plan = self.task_planner.create_plan(
                    description=f"Plano para: {prompt[:50]}...",
                    tasks=tasks_data,
                    strategy=PlanStrategy.DEPENDENCY_ORDER,
                )
                for task in tasks_data:
                    self.stage_ledger.start(task["id"], task["description"])

                self.agi_event_adapter.emit_chat_message(
                    sender="agent",
                    content=f"› [Aura AGI] {UIIcons.SUCCESS} Plan created with LLM: {len(plan.tasks)} tasks "
                    f"(duração estimada: {plan.estimated_duration:.1f}s)",
                )

                return plan

            if not self.problem_decomposer:
                return None

            from aura_cli.core.agents.planning.problem_decomposer import (
                DecompositionStrategy,
            )

            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura AGI] {UIIcons.INFO} Planejamento LLM não disponível, usando decomposição automática...",
            )

            components = self.problem_decomposer.decompose(
                prompt, strategy=DecompositionStrategy.HIERARCHICAL, max_depth=3
            )

            if not components:
                return None

            tasks_data = []
            previous_task_ids: list[str] = []

            for component in components:
                subtasks = self.problem_decomposer.generate_subtasks(component)

                for subtask in subtasks:
                    dependencies = previous_task_ids[-2:] if previous_task_ids else []

                    params = _normalize_subtask_params(subtask.parameters.copy())

                    tasks_data.append(
                        {
                            "id": subtask.id,
                            "description": subtask.description,
                            "priority": component.complexity,
                            "dependencies": dependencies,
                            "parameters": params,
                        }
                    )

                    previous_task_ids.append(subtask.id)

            plan = self.task_planner.create_plan(
                description=f"Plano para: {prompt[:50]}...",
                tasks=tasks_data,
                strategy=PlanStrategy.DEPENDENCY_ORDER,
            )
            for task in tasks_data:
                self.stage_ledger.start(task["id"], task["description"])

            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura AGI] {UIIcons.SUCCESS} Problema decomposto em {len(plan.tasks)} tasks "
                f"(duração estimada: {plan.estimated_duration:.1f}s)",
            )

            return plan

        except Exception as e:
            logger.error(f"Error decomposing problem: {e}", exc_info=True)
            return None

    def select_agent_for_task(self, task: Any, orchestrator: Any) -> str:
        """Select the most appropriate registered agent for a task."""
        if not orchestrator or not getattr(orchestrator, "agents", None):
            return "code_agent"

        params = getattr(task, "parameters", {}) or {}
        requested_agent = str(params.get("agent", "")).strip()
        if requested_agent and requested_agent in orchestrator.agents:
            return requested_agent

        task_type = str(params.get("type", "")).lower()
        preferred_agents = {
            "analyze_code": ["review_agent", "code_agent"],
            "analyze_code_nlp": ["review_agent", "code_agent"],
            "review_file": ["review_agent", "code_agent"],
            "edit_file": ["refactor_agent", "code_agent"],
            "write_file": ["code_agent", "refactor_agent"],
            "read_file": ["code_agent", "review_agent"],
            "list_directory": ["code_agent"],
            "tree_view": ["code_agent"],
            "find_in_files": ["code_agent", "review_agent"],
            "validate_syntax": ["review_agent", "code_agent"],
            "plan_refactoring": ["refactor_agent", "code_agent"],
            "analyze_impact": ["refactor_agent", "review_agent"],
            "apply_refactoring": ["refactor_agent", "code_agent"],
            "suggest_strategy": ["refactor_agent", "review_agent"],
            "run_tests": ["test_agent", "code_agent"],
            "find_related_tests": ["test_agent", "review_agent"],
            "validate_tests_pass": ["test_agent", "code_agent"],
            "generate_tests": ["test_agent", "code_agent"],
        }

        for agent_id in preferred_agents.get(task_type, ["code_agent", "review_agent"]):
            if agent_id in orchestrator.agents:
                return agent_id

        return next(iter(orchestrator.agents.keys()), "code_agent")

    def normalize_task_params(
        self, params: Dict[str, Any], agent_id: str
    ) -> Dict[str, Any]:
        """Normalize task parameters for the selected agent."""
        from aura_cli.core.agents.planning.task_parameter_normalizer import (
            normalize_task_params,
        )

        task_type = str(params.get("type", "")).lower()
        normalized_params, _ = normalize_task_params(
            task_type=task_type,
            params=params.copy(),
            agent_id=agent_id,
            working_directory=str(self.project_root) if self.project_root else None,
        )
        normalized_params["agent"] = agent_id
        return normalized_params

    def request_plan_confirmation(
        self, plan_description: str, tasks_count: int
    ) -> bool:
        """Request user confirmation for a plan."""
        context = InterventionContext(
            tool_name="task_planner",
            tool_args={"tasks_count": tasks_count},
            risk_level=RiskLevel.MEDIUM if tasks_count > 5 else RiskLevel.LOW,
            description=f"Plan with {tasks_count} tasks will be executed",
        )

        prompt = f"📋 Execution plan created:\n{plan_description[:200]}{'...' if len(plan_description) > 200 else ''}\n\nExecute the {tasks_count} tasks?"

        return self.human_intervention_adapter.request_confirmation(
            prompt=prompt, context=context, default=True, timeout=120
        )

    def check_tool_requires_confirmation(
        self, tool_name: str, tool_args: Dict[str, Any]
    ) -> bool:
        """Return True if the tool requires confirmation."""
        confirmation_request = InterventionHelper.build_tool_confirmation_request(
            tool_name,
            tool_args,
        )
        if confirmation_request is None:
            return True

        _risk_level, context, prompt, timeout = confirmation_request

        approved = self.human_intervention_adapter.request_confirmation(
            prompt=prompt,
            context=context,
            default=False,
            timeout=timeout,
        )

        if approved:
            self.agi_event_adapter.emit_chat_message(
                sender="system",
                content=f"✓ Execução de {tool_name} aprovada pelo usuário",
            )
        else:
            self.agi_event_adapter.emit_chat_message(
                sender="system",
                content=f"✗ Execução de {tool_name} cancelada pelo usuário",
            )

        return approved

    def sync_plan_to_todo(self, task_plan, prompt: str) -> None:
        """Sync an AGI plan to the to-do tracker."""
        try:
            from aura_cli.core.todo.todo_tracker import get_todo_tracker

            tracker = get_todo_tracker(str(self.project_root))

            tasks_for_todo = []
            for task in task_plan.tasks:
                task_type = task.parameters.get("type", "task")
                tasks_for_todo.append(
                    {
                        "id": task.id,
                        "description": task.description,
                        "type": task_type,
                        "dependencies": task.dependencies,
                    }
                )

            plan_description = prompt[:50] + "..." if len(prompt) > 50 else prompt
            created_ids = tracker.add_agi_plan(plan_description, tasks_for_todo)

            if created_ids:
                self.agi_event_adapter.emit_chat_message(
                    sender="agent",
                    content=f"› [Aura AGI] {UIIcons.SUCCESS} Plano sincronizado com to-do.md ({len(created_ids)} tasks)",
                )
                logger.info(f"AGI plan synced to TodoTracker: {len(created_ids)} tasks")
            else:
                logger.warning("Failed to sync AGI plan to TodoTracker")

        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not sync AGI plan to TodoTracker: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error syncing AGI plan: {e}", exc_info=True)

    def mark_todo_task_done(self, task_description: str) -> None:
        """Mark a to-do task as done by ID."""
        try:
            from aura_cli.core.todo.todo_tracker import get_todo_tracker

            tracker = get_todo_tracker(str(self.project_root))
            success, _ = tracker.mark_task_by_text(task_description)

            if success:
                logger.debug(
                    f"Marked task as done in TodoTracker: {task_description[:30]}..."
                )
        except (ImportError, AttributeError) as e:
            logger.debug(f"Could not mark task as done in TodoTracker: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error marking task as done: {e}", exc_info=True)
