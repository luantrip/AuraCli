"""Internal DAG-based workflow engine used by the AGI execution engine.

This module is not part of the public ADK API.  For plugin and extension
development use ``aura_cli.adk.workflow`` instead, which exposes the
ADK-stable workflow contracts.

``_CoreWorkflowStep`` / ``Workflow`` define the execution DAG; ``WorkflowExecutor``
runs steps in dependency order with per-step retry and timeout.
``WorkflowStatus`` tracks state (pending/running/completed/failed/cancelled/skipped).
"""

from dataclasses import dataclass, field
import threading
from typing import Any, Callable, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from aura_cli.application.agents.workflow import WorkflowState
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


WorkflowStatus = WorkflowState


@dataclass
class _CoreWorkflowStep:
    """
    Internal AGI execution DAG step.  Not part of the public ADK API.

    Attributes:
        id: Unique step identifier
        name: Step name
        agent_id: ID of the agent that executes this step
        task_description: Task description
        parameters: Task parameters
        dependencies: IDs of steps that must complete before this one
        retry_count: Number of retry attempts on failure
        timeout: Timeout in seconds (None = no timeout)
        condition: Condition function to execute (None = always execute)
    """

    id: str
    name: str
    agent_id: str
    task_description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    retry_count: int = 0
    timeout: Optional[int] = None
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None

    status: WorkflowStatus = WorkflowStatus.PENDING
    task_id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    attempts: int = 0


class Workflow:
    """
    Represents a complete workflow.

    A workflow is a sequence of steps executed by different agents,
    with dependencies and conditions.
    """

    def __init__(self, workflow_id: str, name: str, description: str):
        """
        Initialize a workflow.

        Args:
            workflow_id: Unique workflow identifier
            name: Workflow name
            description: Workflow description
        """
        self.workflow_id = workflow_id
        self.name = name
        self.description = description

        self.steps: Dict[str, _CoreWorkflowStep] = {}
        self.status = WorkflowStatus.PENDING
        self.results: Dict[str, Any] = {}

        self.context: Dict[str, Any] = {}

        logger.info(f"Workflow '{name}' ({workflow_id}) created")

    def add_step(
        self,
        step_id: str,
        name: str,
        agent_id: str,
        task_description: str,
        parameters: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        retry_count: int = 0,
        timeout: Optional[int] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> None:
        """
        Add a step to the workflow.

        Args:
            step_id: Step ID
            name: Step name
            agent_id: ID of the agent that executes
            task_description: Task description
            parameters: Task parameters
            dependencies: IDs of dependent steps
            retry_count: Number of retry attempts
            timeout: Timeout in seconds
            condition: Condition function
        """
        step = _CoreWorkflowStep(
            id=step_id,
            name=name,
            agent_id=agent_id,
            task_description=task_description,
            parameters=parameters or {},
            dependencies=dependencies or [],
            retry_count=retry_count,
            timeout=timeout,
            condition=condition,
        )

        self.steps[step_id] = step
        logger.debug(f"Step {step_id} added to workflow {self.workflow_id}")

    def get_ready_steps(self) -> List[_CoreWorkflowStep]:
        """
        Get steps that can be executed (dependencies satisfied).

        Returns:
            List of steps ready for execution
        """
        ready = []

        for step in self.steps.values():
            if step.status in [WorkflowStatus.COMPLETED, WorkflowStatus.RUNNING]:
                continue

            if step.status == WorkflowStatus.FAILED:
                if step.attempts <= step.retry_count:
                    pass
                else:
                    continue

            deps_ready = True
            for dep_id in step.dependencies:
                dep_step = self.steps.get(dep_id)
                if not dep_step or dep_step.status != WorkflowStatus.COMPLETED:
                    deps_ready = False
                    break

            if not deps_ready:
                continue

            if step.condition and not step.condition(self.context):
                continue

            ready.append(step)

        return ready

    def is_completed(self) -> bool:
        """
        Check if the workflow has completed.

        Returns:
            True if all steps have completed
        """
        return all(
            step.status == WorkflowStatus.COMPLETED for step in self.steps.values()
        )

    def has_failed(self) -> bool:
        """
        Check if the workflow has failed (step failed without retry).

        Returns:
            True if any step failed definitively
        """
        return any(
            step.status == WorkflowStatus.FAILED and step.attempts > step.retry_count
            for step in self.steps.values()
        )

    def get_status_summary(self) -> Dict[str, Any]:
        """
        Get workflow status summary.

        Returns:
            Dictionary with statistics
        """
        status_counts = {}
        for status in WorkflowStatus:
            status_counts[status.value] = sum(
                1 for step in self.steps.values() if step.status == status
            )

        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "status": self.status.value,
            "total_steps": len(self.steps),
            "steps_by_status": status_counts,
            "completed": self.is_completed(),
            "failed": self.has_failed(),
        }


class WorkflowExecutor:
    """
    Workflow executor.

    Manages workflow execution, distributing steps to agents
    and coordinating dependencies.
    """

    def __init__(
        self,
        orchestrator: Any,
        step_wrapper: Optional[
            Callable[["Workflow", "_CoreWorkflowStep", Callable], None]
        ] = None,
    ):
        """
        Initialize the executor.

        Args:
            orchestrator: AgentOrchestrator instance
            step_wrapper: Optional callback that wraps step execution.
                Signature: (workflow, step, execute_fn) -> None
                where execute_fn() performs the actual step execution.
                If provided, the wrapper is responsible for calling execute_fn().
        """
        self.orchestrator = orchestrator
        self.step_wrapper = step_wrapper
        self.active_workflows: Dict[str, Workflow] = {}
        self.stats = get_stats()

        logger.info("WorkflowExecutor initialized")

    def execute_workflow(
        self, workflow: Workflow, max_iterations: int = 1000
    ) -> Dict[str, Any]:
        """
        Execute a complete workflow.

        Args:
            workflow: Workflow to execute
            max_iterations: Maximum iterations

        Returns:
            Dictionary with workflow results
        """
        from aura_cli.core.ui import display_tool_call

        display_tool_call(
            "workflow_execute",
            {
                "workflow_id": workflow.workflow_id,
                "name": workflow.name,
                "steps_count": len(workflow.steps),
            },
        )

        workflow.status = WorkflowStatus.RUNNING
        self.active_workflows[workflow.workflow_id] = workflow

        logger.info(
            f"Iniciando execução do workflow '{workflow.name}' "
            f"({len(workflow.steps)} passos)"
        )

        iteration = 0

        try:
            while iteration < max_iterations:
                if workflow.is_completed():
                    workflow.status = WorkflowStatus.COMPLETED
                    break

                if workflow.has_failed():
                    workflow.status = WorkflowStatus.FAILED
                    break

                ready_steps = workflow.get_ready_steps()
                executable_steps = self._select_steps_for_iteration(ready_steps)

                if not executable_steps:
                    running_steps = [
                        s
                        for s in workflow.steps.values()
                        if s.status == WorkflowStatus.RUNNING
                    ]

                    if not running_steps:
                        logger.warning(
                            f"Workflow {workflow.workflow_id} travado "
                            "(no step can be executed)"
                        )
                        workflow.status = WorkflowStatus.FAILED
                        break

                    iteration += 1
                    continue

                if self._should_run_parallel(executable_steps):
                    self._execute_steps_parallel(workflow, executable_steps)
                else:
                    for step in executable_steps:
                        self._execute_step(workflow, step)

                iteration += 1

            results = {
                "workflow_id": workflow.workflow_id,
                "status": workflow.status.value,
                "iterations": iteration,
                "steps_results": {
                    step_id: {
                        "status": step.status.value,
                        "result": str(step.result)[:500] if step.result else None,
                        "error": step.error,
                    }
                    for step_id, step in workflow.steps.items()
                },
                "context": workflow.context,
            }

            logger.info(
                f"Workflow '{workflow.name}' completed with status "
                f"{workflow.status.value} após {iteration} iterações"
            )

            return results

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            error_msg = f"Error executing workflow {workflow.workflow_id}: {e}"
            logger.error(error_msg, exc_info=True)
            raise

        finally:
            if workflow.workflow_id in self.active_workflows:
                del self.active_workflows[workflow.workflow_id]

    def _execute_step(self, workflow: Workflow, step: _CoreWorkflowStep) -> None:
        """Execute a workflow step."""
        if self.step_wrapper is not None:
            self.step_wrapper(
                workflow, step, lambda: self._execute_step_core(workflow, step)
            )
        else:
            self._execute_step_core(workflow, step)

    def _execute_step_core(self, workflow: Workflow, step: _CoreWorkflowStep) -> None:
        """
        Core step execution logic (separated to support step_wrapper hook).

        Args:
            workflow: Workflow pai
            step: Passo a executar
        """
        step.status = WorkflowStatus.RUNNING
        step.attempts += 1

        logger.info(
            f"Executando passo {step.id} ({step.name}) do workflow "
            f"{workflow.workflow_id}"
        )

        try:
            agent = self.orchestrator.get_agent(step.agent_id)
            if not agent:
                raise ValueError(f"Agent {step.agent_id} not found")

            # Verify agent is properly initialized
            if not hasattr(agent, "add_task"):
                logger.error(
                    f"Agent {step.agent_id} ({agent.__class__.__name__}) does not have add_task method"
                )
                logger.error(
                    f"Agent type: {type(agent)}, Agent MRO: {agent.__class__.__mro__}"
                )
                raise AttributeError(
                    f"Agent {step.agent_id} ({agent.__class__.__name__}) is not properly initialized. "
                    f"Missing add_task method."
                )

            parameters = {**workflow.context, **step.parameters}

            task_id = self.orchestrator.distribute_task(
                task_description=step.task_description,
                agent_id=step.agent_id,
                priority=10,
                parameters=parameters,
            )

            step.task_id = task_id

            result = agent.execute_next_task()

            step.result = result
            step.status = WorkflowStatus.COMPLETED
            workflow.results[step.id] = result

            workflow.context[f"step_{step.id}_result"] = result

            logger.info(
                f"Step {step.id} completed successfully in workflow "
                f"{workflow.workflow_id}"
            )

        except Exception as e:
            step.error = str(e)

            if step.attempts <= step.retry_count:
                step.status = WorkflowStatus.PENDING
                logger.warning(
                    f"Passo {step.id} falhou (tentativa {step.attempts}/"
                    f"{step.retry_count + 1}), será tentado novamente"
                )
            else:
                step.status = WorkflowStatus.FAILED
                logger.error(
                    f"Passo {step.id} falhou definitivamente após "
                    f"{step.attempts} tentativas: {e}",
                    exc_info=True,
                )

    def _should_run_parallel(self, steps: List[_CoreWorkflowStep]) -> bool:
        """Determine if a batch of workflow steps should run in parallel."""
        strategy = getattr(self.orchestrator, "strategy", None)
        return bool(
            strategy and getattr(strategy, "parallel", False) and len(steps) > 1
        )

    def _select_steps_for_iteration(
        self, ready_steps: List[_CoreWorkflowStep]
    ) -> List[_CoreWorkflowStep]:
        """
        Select the steps to execute in the current iteration.

        Parallel workflows are constrained by orchestrator strategy and avoid
        scheduling more than one step per agent in the same batch, which keeps
        agent queues and execution semantics coherent.
        """
        if not ready_steps:
            return []

        strategy = getattr(self.orchestrator, "strategy", None)
        if not strategy or not getattr(strategy, "parallel", False):
            return ready_steps

        max_concurrent = max(1, int(getattr(strategy, "max_concurrent", 1) or 1))
        selected: List[_CoreWorkflowStep] = []
        used_agents = set()

        for step in ready_steps:
            if step.agent_id in used_agents:
                continue

            selected.append(step)
            used_agents.add(step.agent_id)

            if len(selected) >= max_concurrent:
                break

        return selected or ready_steps[:1]

    def _execute_steps_parallel(
        self, workflow: Workflow, steps: List[_CoreWorkflowStep]
    ) -> None:
        """Execute a batch of independent workflow steps in parallel."""
        threads = []
        for step in steps:
            thread = threading.Thread(
                target=self._execute_step,
                args=(workflow, step),
                daemon=True,
            )
            thread.start()
            threads.append(thread)

        for thread in threads:
            thread.join()

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Return the status of a workflow, or None if not found."""
        workflow = self.active_workflows.get(workflow_id)
        if workflow:
            return workflow.get_status_summary()
        return None

    def display_workflow_status(self, workflow_id: str) -> None:
        """Display formatted workflow status."""
        from aura_cli.core.ui_bridge import UIStyles

        workflow = self.active_workflows.get(workflow_id)
        if not workflow:
            error_style = UIStyles.safe_style("ERROR", "red")
            console.print(
                f"[{error_style}]Workflow {workflow_id} not found[/{error_style}]"
            )
            return

        primary_style = UIStyles.safe_style("PRIMARY", "cyan")
        secondary_style = UIStyles.safe_style("SECONDARY", "blue")
        error_style = UIStyles.safe_style("ERROR", "red")
        table = Table(title=f"Workflow: {workflow.name}", show_header=True)
        table.add_column("Passo", style=primary_style)
        table.add_column("Agente", style=secondary_style)
        table.add_column("Status", justify="center")
        table.add_column("Tentativas", justify="right")
        table.add_column("Erro", style=error_style)

        for step in workflow.steps.values():
            status_icon = {
                WorkflowStatus.PENDING: "o",
                WorkflowStatus.RUNNING: "+",
                WorkflowStatus.COMPLETED: "+",
                WorkflowStatus.FAILED: "x",
            }.get(step.status, "?")

            table.add_row(
                step.name,
                step.agent_id,
                f"{status_icon} {step.status.value}",
                str(step.attempts),
                step.error or "-",
            )

        console.print(table)

    def __repr__(self) -> str:
        """Return a string representation of the executor."""
        return f"<WorkflowExecutor(active_workflows={len(self.active_workflows)})>"
