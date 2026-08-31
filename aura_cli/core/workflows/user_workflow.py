"""Optional user-defined workflow automation for Aura CLI.

Declarative multi-step workflows (command/tool/agi/ops/shell steps) with
template variable substitution, dependency ordering and YAML persistence.
Not the canonical agent runtime workflow — use for local automation scripts.
Access via get_workflow_manager().
"""

from dataclasses import dataclass, field
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Any, Callable, Dict, List, Optional
import uuid

from aura_cli.core.logger import get_logger

logger = get_logger(__name__)
try:
    import yaml

    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


@dataclass
class UserWorkflowStep:
    """A single step in a user workflow."""

    id: str
    type: str  # "command", "tool", "agi", "ops", "shell"
    command: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    on_error: str = "stop"  # "stop", "continue", "retry"
    timeout: int = 300  # 5 minutos
    retries: int = 0
    description: str = ""
    status: str = field(
        default="pending"
    )  # pending, running, completed, failed, skipped
    result: Optional[Any] = field(default=None)
    error: Optional[str] = field(default=None)
    started_at: Optional[str] = field(default=None)
    completed_at: Optional[str] = field(default=None)


@dataclass
class UserWorkflow:
    """Manages user-defined multi-step workflows."""

    id: str
    name: str
    description: str = ""
    steps: List[UserWorkflowStep] = field(default_factory=list)
    variables: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict:
        """Serialise to a dict."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [
                {
                    "id": s.id,
                    "type": s.type,
                    "command": s.command,
                    "parameters": s.parameters,
                    "dependencies": s.dependencies,
                    "condition": s.condition,
                    "on_error": s.on_error,
                    "timeout": s.timeout,
                    "retries": s.retries,
                    "description": s.description,
                }
                for s in self.steps
            ],
            "variables": self.variables,
            "tags": self.tags,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "UserWorkflow":
        """Deserialise a workflow from a dict."""
        steps = [
            UserWorkflowStep(
                id=s.get("id", str(uuid.uuid4())[:8]),
                type=s.get("type", "shell"),
                command=s.get("command", ""),
                parameters=s.get("parameters", {}),
                dependencies=s.get("dependencies", []),
                condition=s.get("condition"),
                on_error=s.get("on_error", "stop"),
                timeout=s.get("timeout", 300),
                retries=s.get("retries", 0),
                description=s.get("description", ""),
            )
            for s in data.get("steps", [])
        ]

        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", "Unnamed Workflow"),
            description=data.get("description", ""),
            steps=steps,
            variables=data.get("variables", {}),
            tags=data.get("tags", []),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
        )


class UserWorkflowManager:
    """User workflow manager."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        *,
        tool_executor: Optional[Callable[[str, Dict, int], Any]] = None,
        step_executors: Optional[Dict[str, Callable[[str, Dict, int], Dict]]] = None,
    ):
        """Initialise the workflow."""
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            from aura_cli.core.paths import aura_path

            self.storage_path = aura_path("workflows")

        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._tool_executor = tool_executor
        self._executors: Dict[str, Callable] = {
            "shell": self._execute_shell,
            "tool": self._execute_tool,
        }
        self._executors.update(step_executors or {})

        logger.info(f"UserWorkflowManager initialized: {self.storage_path}")

    def create_workflow(
        self,
        name: str,
        description: str = "",
        steps: Optional[List[Dict]] = None,
        variables: Optional[Dict[str, str]] = None,
        tags: Optional[List[str]] = None,
    ) -> UserWorkflow:
        """Create and register a new workflow."""
        workflow_steps = []
        for i, step_data in enumerate(steps or []):
            step = UserWorkflowStep(
                id=step_data.get("id", f"step_{i + 1}"),
                type=step_data.get("type", "shell"),
                command=step_data.get("command", ""),
                parameters=step_data.get("parameters", {}),
                dependencies=step_data.get("dependencies", []),
                condition=step_data.get("condition"),
                on_error=step_data.get("on_error", "stop"),
                timeout=step_data.get("timeout", 300),
                retries=step_data.get("retries", 0),
                description=step_data.get("description", ""),
            )
            workflow_steps.append(step)

        workflow = UserWorkflow(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description,
            steps=workflow_steps,
            variables=variables or {},
            tags=tags or [],
        )

        self.save_workflow(workflow)

        logger.info(f"Workflow '{name}' created with {len(workflow_steps)} steps")
        return workflow

    def save_workflow(self, workflow: UserWorkflow):
        """Persist a workflow to disk."""
        workflow.updated_at = datetime.now().isoformat()

        if YAML_AVAILABLE:
            file_path = self.storage_path / f"{workflow.id}.yaml"
            with open(file_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    workflow.to_dict(), f, default_flow_style=False, allow_unicode=True
                )
        else:
            file_path = self.storage_path / f"{workflow.id}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(workflow.to_dict(), f, indent=2, ensure_ascii=False)

        logger.debug(f"Workflow {workflow.id} salvo")

    def load_workflow(self, workflow_id: str) -> Optional[UserWorkflow]:
        """Load a workflow from disk."""
        yaml_path = self.storage_path / f"{workflow_id}.yaml"
        json_path = self.storage_path / f"{workflow_id}.json"

        try:
            if yaml_path.exists() and YAML_AVAILABLE:
                with open(yaml_path, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
            elif json_path.exists():
                with open(json_path, encoding="utf-8") as f:
                    data = json.load(f)
            else:
                logger.warning(f"Workflow {workflow_id} not found")
                return None

            return UserWorkflow.from_dict(data)
        except Exception as e:
            logger.error(f"Error loading workflow {workflow_id}: {e}")
            return None

    def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow from disk."""
        yaml_path = self.storage_path / f"{workflow_id}.yaml"
        json_path = self.storage_path / f"{workflow_id}.json"

        deleted = False
        for path in [yaml_path, json_path]:
            if path.exists():
                path.unlink()
                deleted = True

        if deleted:
            logger.info(f"Workflow {workflow_id} removed")
        return deleted

    def list_workflows(self, tags: Optional[List[str]] = None) -> List[UserWorkflow]:
        """List all available workflows."""
        workflows = []

        for ext in ["*.yaml", "*.json"]:
            for file_path in self.storage_path.glob(ext):
                workflow = self.load_workflow(file_path.stem)
                if workflow:
                    if tags and not any(t in workflow.tags for t in tags):
                        continue
                    workflows.append(workflow)

        return sorted(workflows, key=lambda w: w.updated_at, reverse=True)

    def _substitute_variables(
        self, text: str, variables: Dict[str, str], results: Dict[str, Any]
    ) -> str:
        """Substitute variables in text."""
        for key, value in variables.items():
            text = text.replace(f"${{{key}}}", str(value))
            text = text.replace(f"${key}", str(value))
        for step_id, result in results.items():
            text = text.replace(f"${{{step_id}.result}}", str(result.get("output", "")))
            text = text.replace(
                f"${{{step_id}.exit_code}}", str(result.get("exit_code", ""))
            )
        env_pattern = re.compile(r"\$([A-Z_][A-Z0-9_]*)")
        for match in env_pattern.finditer(text):
            env_var = match.group(1)
            env_value = os.environ.get(env_var, "")
            text = text.replace(f"${env_var}", env_value)

        return text

    def _evaluate_condition(self, condition: str, results: Dict[str, Any]) -> bool:
        """Safely evaluate an execution condition (no eval)."""
        if not condition:
            return True

        try:
            context: Dict[str, Any] = {"true": True, "false": False}
            for step_id, result in results.items():
                context[f"{step_id}_success"] = result.get("success", False)
                context[f"{step_id}_exit_code"] = result.get("exit_code", -1)

            return self._safe_eval(condition.strip().lower(), context)
        except Exception as e:
            logger.warning(f"Error evaluating condition '{condition}': {e}")
            return True

    def _safe_eval(self, expr: str, ctx: Dict[str, Any]) -> bool:
        """Safely evaluate a simple expression string."""
        # OR has lower precedence
        if " or " in expr:
            return any(self._safe_eval(p.strip(), ctx) for p in expr.split(" or "))
        # AND
        if " and " in expr:
            return all(self._safe_eval(p.strip(), ctx) for p in expr.split(" and "))
        # NOT
        if expr.startswith("not "):
            return not self._safe_eval(expr[4:].strip(), ctx)
        # Equality == and != comparisons
        for op, fn in (("==", lambda a, b: a == b), ("!=", lambda a, b: a != b)):
            if op in expr:
                left, right = (s.strip() for s in expr.split(op, 1))
                return fn(
                    self._resolve_value(left, ctx), self._resolve_value(right, ctx)
                )
        # Valor simples
        return bool(self._resolve_value(expr, ctx))

    @staticmethod
    def _resolve_value(token: str, ctx: Dict[str, Any]) -> Any:
        """Resolve a value, expanding variable references."""
        if token in ctx:
            return ctx[token]
        if token.lstrip("-").isdigit():
            return int(token)
        if token in ("true", "false"):
            return token == "true"
        return token

    def _topological_sort(
        self, steps: List[UserWorkflowStep]
    ) -> List[UserWorkflowStep]:
        """Sort steps respecting dependencies."""
        step_map = {s.id: s for s in steps}
        visited = set()
        result = []

        def visit(step_id: str):
            """Visit step in topological sort."""
            if step_id in visited:
                return
            visited.add(step_id)

            step = step_map.get(step_id)
            if step:
                for dep_id in step.dependencies:
                    visit(dep_id)
                result.append(step)

        for step in steps:
            visit(step.id)

        return result

    def _execute_step(
        self,
        step: UserWorkflowStep,
        command: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a step only through an explicitly configured adapter."""
        executor = self._executors.get(step.type)
        if executor is None:
            return {
                "success": False,
                "error": f"Workflow step executor is not configured: {step.type}",
            }
        return executor(command, params, step.timeout)

    def execute_workflow(
        self,
        workflow_id: str,
        variables: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
        on_step_complete: Optional[Callable] = None,
    ) -> Dict[str, Any]:
        """Execute a workflow by name or ID."""
        workflow = self.load_workflow(workflow_id)
        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")
        all_variables = {**workflow.variables, **(variables or {})}
        sorted_steps = self._topological_sort(workflow.steps)

        results: Dict[str, Any] = {}
        failed = False

        logger.info(
            f"Executando workflow '{workflow.name}' ({len(sorted_steps)} steps)"
        )

        for step in sorted_steps:
            deps_ok = all(
                results.get(dep_id, {}).get("success", False)
                for dep_id in step.dependencies
            )

            if not deps_ok:
                step.status = "skipped"
                step.error = "Dependência failed"
                results[step.id] = {
                    "success": False,
                    "skipped": True,
                    "error": "Dependency failed",
                }
                continue
            if not self._evaluate_condition(step.condition or "", results):
                step.status = "skipped"
                results[step.id] = {
                    "success": True,
                    "skipped": True,
                    "reason": "Condition not met",
                }
                continue
            command = self._substitute_variables(step.command, all_variables, results)
            params = {
                k: self._substitute_variables(str(v), all_variables, results)
                for k, v in step.parameters.items()
            }

            if dry_run:
                logger.info(f"[DRY RUN] {step.type}: {command}")
                results[step.id] = {
                    "success": True,
                    "dry_run": True,
                    "command": command,
                }
                continue
            step.status = "running"
            step.started_at = datetime.now().isoformat()

            attempt = 0
            max_attempts = step.retries + 1

            while attempt < max_attempts:
                attempt += 1

                try:
                    result = self._execute_step(step, command, params)

                    step.status = "completed" if result.get("success") else "failed"
                    step.result = result
                    step.completed_at = datetime.now().isoformat()

                    results[step.id] = result

                    if result.get("success"):
                        break
                    elif attempt < max_attempts:
                        logger.warning(
                            f"Passo {step.id} failed, tentativa {attempt}/{max_attempts}"
                        )

                except Exception as e:
                    step.status = "failed"
                    step.error = str(e)
                    step.completed_at = datetime.now().isoformat()

                    results[step.id] = {
                        "success": False,
                        "error": str(e),
                    }

                    if attempt < max_attempts:
                        logger.warning(
                            f"Passo {step.id} erro: {e}, tentativa {attempt}/{max_attempts}"
                        )
            if on_step_complete:
                on_step_complete(step, results[step.id])
            if not results[step.id].get("success"):
                if step.on_error == "stop":
                    failed = True
                    break
                elif step.on_error == "continue":
                    continue

        logger.info(
            f"Workflow '{workflow.name}' completed: {'success' if not failed else 'failed'}"
        )

        return {
            "workflow_id": workflow_id,
            "success": not failed,
            "steps": results,
            "completed_at": datetime.now().isoformat(),
        }

    def _execute_shell(self, command: str, params: Dict, timeout: int) -> Dict:
        """Execute a shell command step."""
        from aura_cli.core.logger import get_logger
        from aura_cli.core.tools.shell import _is_safe_command

        logger = get_logger(__name__)

        if not _is_safe_command(command):
            reason = "Command contains dangerous patterns or blocked commands"
            logger.warning(f"Workflow command blocked: {command[:50]}...")
            return {
                "success": False,
                "error": f"Command blocked for security: {reason}",
            }

        try:
            from aura_cli.core.utils.safe_subprocess import SafeSubprocess

            executor = SafeSubprocess(timeout_seconds=timeout)
            result = executor.run_shell(command, cwd=params.get("cwd"))

            return {
                "success": result.success,
                "exit_code": result.exit_code,
                "output": result.stdout,
                "error_output": result.stderr,
            }
        except subprocess.TimeoutExpired:
            logger.warning(f"Workflow command timeout: {command[:50]}...")
            return {
                "success": False,
                "error": f"Timeout after {timeout}s",
            }
        except FileNotFoundError as e:
            logger.error(f"Command not found in workflow: {command}", exc_info=True)
            return {
                "success": False,
                "error": f"Command not found: {e}",
            }
        except PermissionError as e:
            logger.error(f"Permission denied in workflow: {command}", exc_info=True)
            return {
                "success": False,
                "error": f"Permission denied: {e}",
            }
        except OSError as e:
            logger.error(f"OS error in workflow command: {command}", exc_info=True)
            return {
                "success": False,
                "error": f"System error: {e}",
            }

    def _execute_tool(self, tool_name: str, params: Dict, timeout: int) -> Dict:
        """Execute a tool step."""
        if self._tool_executor is None:
            return {
                "success": False,
                "error": "Tool execution adapter is not configured",
            }
        try:
            result = self._tool_executor(tool_name, params, timeout)

            return {
                "success": result is not None,
                "output": result,
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }


_workflow_manager: Optional[UserWorkflowManager] = None


def get_workflow_manager() -> UserWorkflowManager:
    """Return the global workflow manager singleton."""
    global _workflow_manager
    if _workflow_manager is None:
        _workflow_manager = UserWorkflowManager()
    return _workflow_manager
