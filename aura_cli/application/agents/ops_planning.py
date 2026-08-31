"""Planning and routing policies for the Ops worker adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence


@dataclass(frozen=True)
class OpsWorkflowStepSpec:
    """Toolkit-neutral description of one concrete Ops workflow step."""

    step_id: str
    name: str
    agent_id: str
    task_description: str
    parameters: Mapping[str, Any]
    dependencies: tuple[str, ...]
    retry_count: int = 1


@dataclass(frozen=True)
class OpsWorkflowBlueprint:
    """Application plan translated for a workflow execution adapter."""

    workflow_id: str
    name: str
    description: str
    steps: tuple[OpsWorkflowStepSpec, ...]


def render_delegation_context(payload: Mapping[str, Any] | None) -> str:
    """Render bounded structured context received from the general chat."""
    if not payload:
        return ""
    lines = [
        "**CHAT DELEGATION PAYLOAD:**",
        f"- source: {payload.get('source', 'unknown')}",
        f"- primary_request: {payload.get('primary_request', '')}",
        f"- project_root: {payload.get('project_root', '')}",
        f"- current_chat_model: {payload.get('current_chat_model', '')}",
        f"- constitution_active: {payload.get('constitution_active', False)}",
    ]
    if payload.get("delegation_mode"):
        lines.append(f"- delegation_mode: {payload['delegation_mode']}")
    for field in ("supporting_context", "recent_chat_excerpt"):
        if value := payload.get(field):
            lines.extend([f"- {field}:", str(value)[:1000]])
    lines.extend(
        [
            "- Use the payload as structured context from the general chat.",
            "- Prefer primary_request as the canonical task.",
        ]
    )
    return "\n".join(lines)


def build_effective_ops_prompt(prompt: str, payload: Mapping[str, Any] | None) -> str:
    """Wrap the worker request with its structured chat handoff when present."""
    if not payload:
        return prompt
    return "\n".join(
        [
            "[CHAT DELEGATION HANDOFF]",
            render_delegation_context(payload),
            "Task to execute:",
            prompt,
            "[/CHAT DELEGATION HANDOFF]",
        ]
    )


def build_ops_planning_prompt(
    mode: str,
    payload: Mapping[str, Any] | None = None,
    workspace_diff: str = "",
) -> str:
    """Build the constrained JSON planning prompt for an Ops execution mode."""
    payload_section = render_delegation_context(payload)
    return f"""Você é um planejador de tarefas DevOps especializado. Analise o pedido do usuário e crie um plano estruturado de tarefas.

**MODO ATUAL:** {mode}

{payload_section}

{workspace_diff}

**FORMATO DE RESPOSTA (JSON):**
{{
  "tasks": [
    {{
      "id": "tarefa_1",
      "description": "Descrição clara da tarefa",
      "type": "read_file|write_file|list_directory|git_status|git_diff|git_diff_context|git_log|docker_ps|docker_logs|cloudflare_tunnel_create|cloudflare_pages_deploy|run_shell_command|tree_view",
      "agent": "ops_code_agent",
      "priority": 5,
      "dependencies": [],
      "parameters": {{
        "path": "caminho/do/arquivo",
        "command": "comando se for git/docker",
        "name": "nome do tunnel ou projeto",
        "url": "url local para tunnel",
        "directory": "diretório para deploy",
        "mode": "{mode}",
        ...
      }}
    }}
  ]
}}

**REGRAS:**
1. Cada tarefa DEVE ter TODOS os parâmetros necessários
2. Para read_file, write_file, list_directory, tree_view: SEMPRE inclua "path" (use "." se não especificado)
3. IMPORTANTE: Só crie tarefas Git (git_status, git_diff, git_log) se o usuário explicitamente pedir ou se for necessário para a análise
4. IMPORTANTE: Só crie tarefas Docker (docker_ps, docker_logs) se o usuário explicitamente pedir ou se for necessário para a análise
5. Se o usuário não mencionar Git ou Docker, NÃO crie tarefas relacionadas a eles
6. Para git_status: Não precisa de parâmetros adicionais
7. Para git_diff: Opcionalmente inclua "file_path" ou "path"
8. Para git_diff_context: Use para obter o estado completo, incluindo arquivos não rastreados.
9. Para git_log: Opcionalmente inclua "limit" (padrão: 10)
9. Para docker_ps: Opcionalmente inclua "all" (true/false)
10. Para docker_logs: SEMPRE inclua "container" (nome do container)
11. Para cloudflare_tunnel_create: Inclua "name" e "url"
12. Para cloudflare_pages_deploy: Inclua "directory" (padrão ".") e opcionalmente "project_name"
13. Para run_shell_command: SEMPRE inclua "command" (comando a executar)
14. SEMPRE inclua "mode": "{mode}" nos parâmetros
15. Comece sempre com list_directory(".") para entender o projeto

Retorne APENAS o JSON, sem markdown, sem explicações."""


def select_ops_agent(task: Any, available_agents: Iterable[str]) -> str:
    """Route a task to an available specialized Ops agent."""
    agents = set(available_agents)
    parameters = getattr(task, "parameters", {})
    task_type = str(parameters.get("type", "")).casefold()
    description = str(getattr(task, "description", "")).casefold()
    routes = (
        (
            "ops_git_agent",
            {
                "git_status",
                "git_diff",
                "git_log",
                "git_commit",
                "git_branch",
                "git_smart",
            },
            {"git", "commit", "branch", "merge", "rebase", "push", "pull", "checkout"},
        ),
        (
            "ops_docker_agent",
            {
                "docker_ps",
                "docker_logs",
                "docker_build",
                "docker_compose",
                "docker_exec",
            },
            {
                "docker",
                "container",
                "compose",
                "image",
                "dockerfile",
                "kubernetes",
                "k8s",
            },
        ),
    )
    for agent_id, task_types, keywords in routes:
        if agent_id in agents and (
            task_type in task_types
            or any(keyword in description for keyword in keywords)
        ):
            return agent_id
    return "ops_code_agent"


def valid_workflow_tasks(tasks: Sequence[Any]) -> list[Any]:
    """Apply parameter defaults and retain tasks accepted by the workflow path."""
    valid = []
    path_default_operations = {
        "read_file",
        "write_file",
        "edit_file",
        "list_directory",
        "tree_view",
    }
    for task in tasks:
        parameters = task.parameters
        task_type = str(parameters.get("type", "")).casefold()
        if task_type in path_default_operations:
            parameters.setdefault("path", ".")
        elif task_type == "find_in_files" and (
            "pattern" not in parameters or "path" not in parameters
        ):
            continue
        valid.append(task)
    return valid


def build_ops_workflow_blueprint(
    task_plan: Any,
    *,
    mode: str,
    prompt: str,
    workflow_id: str,
    available_agents: Iterable[str],
) -> OpsWorkflowBlueprint:
    """Translate a planner result into a framework-neutral workflow blueprint."""
    agents = set(available_agents)
    steps = []
    for task in task_plan.tasks:
        agent_id = select_ops_agent(task, agents)
        if agent_id not in agents:
            agent_id = "ops_code_agent"
        steps.append(
            OpsWorkflowStepSpec(
                step_id=str(task.id),
                name=str(task.description)[:50],
                agent_id=agent_id,
                task_description=str(task.description),
                parameters=dict(task.parameters),
                dependencies=tuple(task.dependencies),
            )
        )
    return OpsWorkflowBlueprint(
        workflow_id=workflow_id,
        name=f"Ops Workflow ({mode}): {prompt[:50]}...",
        description=prompt,
        steps=tuple(steps),
    )


def build_ops_workflow_result(
    *,
    prompt: str,
    model: str,
    mode: str,
    workflow_result: Mapping[str, Any],
    context_summary: Any,
    tools_used: Iterable[str],
    delegation_payload: Mapping[str, Any] | None,
    workspace_diff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stable worker result emitted after a workflow execution."""
    return {
        "status": "completed",
        "prompt": prompt,
        "model": model,
        "mode": mode,
        "workflow_result": dict(workflow_result),
        "context_summary": context_summary,
        "tools_used": list(tools_used),
        "generated_files": [],
        "edited_files": [],
        "analyzed_files": [],
        "files_touched": [],
        "delegation_payload": delegation_payload,
        "workspace_diff": dict(workspace_diff or {}),
    }


__all__ = [
    "OpsWorkflowBlueprint",
    "OpsWorkflowStepSpec",
    "build_effective_ops_prompt",
    "build_ops_planning_prompt",
    "build_ops_workflow_blueprint",
    "build_ops_workflow_result",
    "render_delegation_context",
    "select_ops_agent",
    "valid_workflow_tasks",
]
