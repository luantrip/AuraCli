"""
Ops Code Agent - Specialized Agent for DevOps Operations.

This agent extends CodeAgent with support for specific Ops tasks
like git_status, docker_ps, etc.
"""

import json
import subprocess
from typing import Any, Optional, Tuple

from aura_cli.core.agents.agent_base import AgentTask
from aura_cli.core.agents.specialized_agents.code_agent import CodeAgent
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class OpsCodeAgent(CodeAgent):
    """
    Specialised agent for DevOps operations.

    Extends CodeAgent with support for:
    - Git operations (git_status, git_diff, git_log)
    - Docker operations (docker_ps, docker_logs)
    - System and infrastructure operations

    Checks availability and asks the user before executing.
    """

    def __init__(self, agent_id: str = "ops_code_agent"):
        """Initialise the Ops Code Agent."""
        super().__init__(agent_id=agent_id)
        self.name = "Ops Code Agent"
        self.role = "devops_agent"
        self._git_enabled: Optional[bool] = None
        self._docker_enabled: Optional[bool] = None

    def _execute_task(self, task: AgentTask) -> Any:
        """Execute a task with support for Ops-specific types."""
        task_type = task.parameters.get("type", "unknown")

        if task_type == "git_status":
            return self._handle_git_status(task)
        elif task_type == "git_dif":
            return self._handle_git_diff(task)
        elif task_type == "git_log":
            return self._handle_git_log(task)
        elif task_type == "docker_ps":
            return self._handle_docker_ps(task)
        elif task_type == "docker_logs":
            return self._handle_docker_logs(task)
        elif task_type == "run_shell_command":
            return self._handle_shell_command(task)
        else:
            return super()._execute_task(task)

    def _check_git_available(self) -> Tuple[bool, str]:
        """Return (available, message) for Git availability."""
        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if result.returncode != 0:
                return False, "Git não está instalado. Instale o Git primeiro."
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Git não está disponível. Instale o Git ou configure o PATH."

        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                capture_output=True,
                text=True,
                check=False,
                timeout=2,
            )
            if result.returncode != 0:
                return (
                    False,
                    "Não está em um repositório Git. Inicialize um repositório ou navegue até um.",
                )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False, "Error verifying Git repository."

        return True, ""

    def _check_docker_available(self) -> bool:
        """Return True if Docker is available and running."""
        try:
            result = subprocess.run(
                ["docker", "ps"], capture_output=True, text=True, check=False, timeout=2
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _ask_user_permission(self, tool_name: str, tool_description: str) -> bool:
        """Ask the user for permission to use a tool."""

        from aura_cli.core.tools.human_intervention_adapter import (
            request_local_confirmation,
        )
        from aura_cli.core.ui_bridge import UIIcons

        question_icon = getattr(UIIcons, "QUESTION", UIIcons.INFO)
        message = f"{question_icon} Usar {tool_name} para {tool_description}?"
        return request_local_confirmation(message, default=True)

    def _handle_git_status(self, task: AgentTask) -> str:
        """Handle a git status request."""
        git_available, error_msg = self._check_git_available()
        if not git_available:
            return error_msg

        if self._git_enabled is None:
            self._git_enabled = self._ask_user_permission(
                "Git", "verificar status do repositório"
            )

        if not self._git_enabled:
            return "Operação Git cancelada pelo usuário."

        from aura_cli.core.ops_tools.git import git_status

        return git_status()

    def _handle_git_diff(self, task: AgentTask) -> str:
        """Handle a git diff request."""
        git_available, error_msg = self._check_git_available()
        if not git_available:
            return error_msg

        if self._git_enabled is None:
            self._git_enabled = self._ask_user_permission("Git", "mostrar diferenças")

        if not self._git_enabled:
            return "Operação Git cancelada pelo usuário."

        from aura_cli.core.ops_tools.git import git_diff

        file_path = task.parameters.get("file_path") or task.parameters.get("path")
        return git_diff(file=file_path)

    def _handle_git_log(self, task: AgentTask) -> str:
        """Handle a git log request."""
        git_available, error_msg = self._check_git_available()
        if not git_available:
            return error_msg

        if self._git_enabled is None:
            self._git_enabled = self._ask_user_permission("Git", "mostrar histórico")

        if not self._git_enabled:
            return "Operação Git cancelada pelo usuário."

        from aura_cli.core.ops_tools.git import git_log

        limit = task.parameters.get("limit", 10)
        return git_log(limit=limit)

    def _handle_docker_ps(self, task: AgentTask) -> str:
        """Handle a docker ps request."""
        if not self._check_docker_available():
            return "Docker não está disponível ou não está rodando. Inicie o Docker ou instale-o."

        if self._docker_enabled is None:
            self._docker_enabled = self._ask_user_permission(
                "Docker", "listar containers"
            )

        if not self._docker_enabled:
            return "Operação Docker cancelada pelo usuário."

        from aura_cli.core.ops_tools.docker import docker_ps

        all_containers = task.parameters.get("all", False)
        result = docker_ps(show_all=all_containers)
        return result if isinstance(result, str) else json.dumps(result, indent=2)

    def _handle_docker_logs(self, task: AgentTask) -> str:
        """Show Docker logs."""
        if not self._check_docker_available():
            return "Docker não está disponível ou não está rodando. Inicie o Docker ou instale-o."

        if self._docker_enabled is None:
            container = task.parameters.get("container", "container")
            self._docker_enabled = self._ask_user_permission(
                "Docker", f"mostrar logs do container {container}"
            )

        if not self._docker_enabled:
            return "Operação Docker cancelada pelo usuário."

        from aura_cli.core.ops_tools.docker import docker_logs

        container = task.parameters.get("container")
        if not container:
            return "Erro: Parâmetro 'container' é obrigatório para docker_logs"
        tail = task.parameters.get("tail", 100)
        result = docker_logs(container=container, tail=tail)
        return result if isinstance(result, str) else "\n".join(result)

    def _handle_shell_command(self, task: AgentTask) -> str:
        """Execute a shell command."""
        from aura_cli.core.tools.shell import run_shell_command

        command = task.parameters.get("command")
        if not command:
            return "Erro: Parâmetro 'command' é obrigatório para run_shell_command"
        return run_shell_command(command)
