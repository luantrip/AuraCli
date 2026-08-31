"""ADK Workflow System — orchestration for multi-step agent tasks."""

from __future__ import annotations

import asyncio
import contextlib
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Protocol
import uuid

from .contracts import AgentResponse


class Agent(Protocol):
    """Minimal agent port required by the workflow engine."""

    async def execute(self, task: str, **kwargs: Any) -> AgentResponse: ...


class WorkflowCancelledError(RuntimeError):
    """Internal cooperative cancellation signal for a workflow step."""


logger = logging.getLogger(__name__)


class WorkflowState(Enum):
    """Workflow execution states."""

    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class StepState(Enum):
    """Individual step states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """
    A single step in a workflow.

    Attributes:
        id: Unique identifier
        name: Human-readable name
        agent: Agent to execute this step
        task: Task description or callable
        dependencies: IDs of steps that must complete first
        condition: Optional condition function
        retry_count: Number of retries on failure
        timeout: Timeout in seconds
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    agent: Optional[Agent] = None
    task: str = ""
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    retry_count: int = 0
    timeout: float = 300.0

    state: StepState = StepState.PENDING
    result: Optional[AgentResponse] = None
    error: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    retries: int = 0

    @property
    def duration(self) -> Optional[float]:
        """Get step duration in seconds."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None

    def reset(self) -> None:
        """Reset step state for re-execution."""
        self.state = StepState.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.retries = 0


@dataclass
class WorkflowResult:
    """Result of a workflow execution."""

    workflow_id: str
    state: WorkflowState
    steps: List[WorkflowStep]
    outputs: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def duration(self) -> float:
        """Get total workflow duration."""
        return self.end_time - self.start_time

    @property
    def success(self) -> bool:
        """Check if workflow completed successfully."""
        return self.state == WorkflowState.COMPLETED

    @property
    def failed_steps(self) -> List[WorkflowStep]:
        """Get list of failed steps."""
        return [s for s in self.steps if s.state == StepState.FAILED]

    def to_dict(self) -> Dict[str, Any]:
        """Return a bounded, JSON-safe workflow snapshot."""
        return {
            "workflow_id": self.workflow_id,
            "state": self.state.value,
            "outputs": {str(key): str(value) for key, value in self.outputs.items()},
            "error": self.error,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "steps": [
                {
                    "id": step.id,
                    "name": step.name,
                    "state": step.state.value,
                    "error": step.error,
                    "retries": step.retries,
                    "start_time": step.start_time,
                    "end_time": step.end_time,
                    "result": (
                        str(step.result.content) if step.result is not None else None
                    ),
                }
                for step in self.steps
            ],
        }

    def get_step_result(self, step_id: str) -> Optional[Any]:
        """Get result of a specific step."""
        return self.outputs.get(step_id)


class Workflow:
    """Orchestrates multi-step agent workflows with dependency resolution.

    Steps are added via add_step() with optional depends_on references.
    Independent steps run in parallel (up to max_parallel). Run with
    await workflow.run().
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        max_parallel: int = 3,
    ):
        """
        Initialize workflow.

        Args:
            name: Workflow name
            description: Workflow description
            max_parallel: Maximum parallel step execution
        """
        self.id = str(uuid.uuid4())[:8]
        self.name = name
        self.description = description
        self.max_parallel = max_parallel

        self._steps: Dict[str, WorkflowStep] = {}
        self._order: List[str] = []
        self._state = WorkflowState.PENDING
        self._outputs: Dict[str, Any] = {}
        self._cancel_requested = threading.Event()

        # Callbacks
        self._on_step_start: List[Callable[[WorkflowStep], None]] = []
        self._on_step_complete: List[Callable[[WorkflowStep], None]] = []
        self._on_workflow_complete: List[Callable[[WorkflowResult], None]] = []

    @property
    def state(self) -> WorkflowState:
        """Get workflow state."""
        return self._state

    @property
    def steps(self) -> List[WorkflowStep]:
        """Get all steps in order."""
        return [self._steps[sid] for sid in self._order]

    def add_step(
        self,
        agent: Agent,
        task: str,
        name: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        retry_count: int = 0,
        timeout: float = 300.0,
    ) -> str:
        """
        Add a step to the workflow.

        Args:
            agent: Agent to execute this step
            task: Task description (can include {step_name.output} placeholders)
            name: Optional step name (auto-generated if not provided)
            depends_on: List of step names this step depends on
            condition: Optional function to determine if step should run
            retry_count: Number of retries on failure
            timeout: Step timeout in seconds

        Returns:
            Step ID
        """
        step_id = name or f"step_{len(self._steps) + 1}"

        step = WorkflowStep(
            id=step_id,
            name=name or step_id,
            agent=agent,
            task=task,
            dependencies=depends_on or [],
            condition=condition,
            retry_count=retry_count,
            timeout=timeout,
        )

        self._steps[step_id] = step
        self._order.append(step_id)

        return step_id

    def remove_step(self, step_id: str) -> bool:
        """Remove a step from the workflow."""
        if step_id in self._steps:
            del self._steps[step_id]
            self._order.remove(step_id)
            return True
        return False

    def get_step(self, step_id: str) -> Optional[WorkflowStep]:
        """Get a step by ID."""
        return self._steps.get(step_id)

    async def run(self, inputs: Optional[Dict[str, Any]] = None) -> WorkflowResult:
        """
        Execute the workflow.

        Args:
            inputs: Optional initial inputs

        Returns:
            WorkflowResult with execution details
        """
        self._state = WorkflowState.RUNNING
        self._outputs = inputs or {}
        start_time = time.time()

        for step in self._steps.values():
            step.reset()

        try:
            pending = set(self._order)
            completed: set[str] = set()
            failed: set[str] = set()

            while pending:
                if (
                    self._cancel_requested.is_set()
                    or self._state == WorkflowState.CANCELLED
                ):
                    self._state = WorkflowState.CANCELLED
                    self._mark_pending_cancelled(pending)
                    return self._build_result(
                        start_time,
                        error="Workflow cancelled cooperatively",
                    )

                ready = []
                for step_id in pending:
                    step = self._steps[step_id]
                    deps_met = all(d in completed for d in step.dependencies)
                    if deps_met:
                        ready.append(step_id)

                if not ready:
                    # Check if blocked by failed dependencies (not a deadlock)
                    blocked_by_failure = any(
                        any(d in failed for d in self._steps[sid].dependencies)
                        for sid in pending
                    )
                    if blocked_by_failure:
                        self._state = WorkflowState.FAILED
                        return WorkflowResult(
                            workflow_id=self.id,
                            state=self._state,
                            steps=list(self._steps.values()),
                            outputs=self._outputs,
                            error="Workflow stopped: pending steps blocked by failed dependencies",
                            start_time=start_time,
                            end_time=time.time(),
                        )
                    raise RuntimeError("Workflow deadlock detected")

                batch = ready[: self.max_parallel]
                tasks = [self._execute_step(self._steps[sid]) for sid in batch]

                results = await asyncio.gather(*tasks, return_exceptions=True)

                batch_result = self._process_batch_results(
                    batch,
                    results,
                    pending=pending,
                    completed=completed,
                    failed=failed,
                    start_time=start_time,
                )
                if batch_result is not None:
                    return batch_result

            self._state = WorkflowState.COMPLETED

        except Exception as e:
            self._state = WorkflowState.FAILED
            logger.error(f"Workflow failed: {e}")

            return WorkflowResult(
                workflow_id=self.id,
                state=self._state,
                steps=list(self._steps.values()),
                outputs=self._outputs,
                error=str(e),
                start_time=start_time,
                end_time=time.time(),
            )

        workflow_result = WorkflowResult(
            workflow_id=self.id,
            state=self._state,
            steps=list(self._steps.values()),
            outputs=self._outputs,
            start_time=start_time,
            end_time=time.time(),
        )

        for callback in self._on_workflow_complete:
            try:
                callback(workflow_result)
            except Exception as e:
                logger.error(f"Callback error: {e}")

        return workflow_result

    def _process_batch_results(
        self,
        batch: list[str],
        results: list[Any],
        *,
        pending: set[str],
        completed: set[str],
        failed: set[str],
        start_time: float,
    ) -> WorkflowResult | None:
        """Apply one batch result and return an early terminal result when needed."""
        for step_id, result in zip(batch, results, strict=True):
            step = self._steps[step_id]

            if isinstance(result, WorkflowCancelledError):
                step.state = StepState.CANCELLED
                self._state = WorkflowState.CANCELLED
                self._mark_pending_cancelled(pending - {step_id})
                return self._build_result(
                    start_time,
                    error="Workflow cancelled cooperatively",
                )

            if isinstance(result, Exception):
                step.state = StepState.FAILED
                step.error = str(result)

                if step.retries >= step.retry_count:
                    self._state = WorkflowState.FAILED
                    return WorkflowResult(
                        workflow_id=self.id,
                        state=self._state,
                        steps=list(self._steps.values()),
                        outputs=self._outputs,
                        error=f"Step '{step.name}' failed: {step.error}",
                        start_time=start_time,
                        end_time=time.time(),
                    )

            pending.remove(step_id)
            if isinstance(result, Exception):
                failed.add(step_id)
            else:
                completed.add(step_id)
        return None

    async def _execute_step(self, step: WorkflowStep) -> None:
        """Execute a single step with cooperative cancellation checks."""
        if self._cancel_requested.is_set() or self._state == WorkflowState.CANCELLED:
            step.state = StepState.CANCELLED
            step.error = "Workflow cancelled cooperatively"
            raise WorkflowCancelledError(step.error)

        if step.condition and not step.condition(self._outputs):
            step.state = StepState.SKIPPED
            return

        for callback in self._on_step_start:
            with contextlib.suppress(Exception):
                callback(step)

        step.state = StepState.RUNNING
        step.start_time = time.time()

        while True:
            try:
                task = self._interpolate_task(step.task)

                if step.agent:
                    result = await asyncio.wait_for(
                        step.agent.execute(task), timeout=step.timeout
                    )
                    if (
                        self._cancel_requested.is_set()
                        or self._state == WorkflowState.CANCELLED
                    ):
                        step.state = StepState.CANCELLED
                        step.error = "Workflow cancelled cooperatively"
                        raise WorkflowCancelledError(step.error)
                    step.result = result
                    self._outputs[step.id] = result.content

                    if result.success:
                        step.state = StepState.COMPLETED
                    else:
                        raise RuntimeError(result.error or "Step execution failed")
                else:
                    self._outputs[step.id] = task
                    step.state = StepState.COMPLETED

                break  # success, exit loop

            except asyncio.TimeoutError:
                step.error = f"Step timed out after {step.timeout}s"
                raise
            except Exception as e:
                step.error = str(e)
                step.retries += 1

                if step.retries <= step.retry_count:
                    logger.warning(
                        f"Step '{step.name}' failed, retrying ({step.retries}/{step.retry_count})"
                    )
                    continue  # retry iteratively
                else:
                    raise
            finally:
                step.end_time = time.time()

                for callback in self._on_step_complete:
                    with contextlib.suppress(Exception):
                        callback(step)

    def _interpolate_task(self, task: str) -> str:
        """Interpolate task string with step outputs."""
        result = task
        for step_id, output in self._outputs.items():
            result = result.replace(f"{{{step_id}.output}}", str(output))
            result = result.replace(f"{{{step_id}}}", str(output))
        return result

    def pause(self) -> None:
        """Pause workflow execution."""
        if self._state == WorkflowState.RUNNING:
            self._state = WorkflowState.PAUSED

    def resume(self) -> None:
        """Resume paused workflow."""
        if self._state == WorkflowState.PAUSED:
            self._state = WorkflowState.RUNNING

    def cancel(self) -> None:
        """Request cooperative cancellation of the workflow."""
        self._cancel_requested.set()
        self._state = WorkflowState.CANCELLED

    def _mark_pending_cancelled(self, step_ids: Any) -> None:
        """Mark not-yet-started steps as cancelled in the result snapshot."""
        for step_id in step_ids:
            step = self._steps.get(step_id)
            if step is not None and step.state == StepState.PENDING:
                step.state = StepState.CANCELLED
                step.error = "Workflow cancelled cooperatively"

    def _build_result(
        self, start_time: float, *, error: str | None = None
    ) -> WorkflowResult:
        """Build a consistent result for early terminal transitions."""
        return WorkflowResult(
            workflow_id=self.id,
            state=self._state,
            steps=list(self._steps.values()),
            outputs=self._outputs,
            error=error,
            start_time=start_time,
            end_time=time.time(),
        )

    def on_step_start(self, callback: Callable[[WorkflowStep], None]) -> None:
        """Register callback for step start."""
        self._on_step_start.append(callback)

    def on_step_complete(self, callback: Callable[[WorkflowStep], None]) -> None:
        """Register callback for step completion."""
        self._on_step_complete.append(callback)

    def on_complete(self, callback: Callable[[WorkflowResult], None]) -> None:
        """Register callback for workflow completion."""
        self._on_workflow_complete.append(callback)

    def visualize(self) -> str:
        """Generate ASCII visualization of workflow."""
        lines = [f"Workflow: {self.name}", "=" * 40]

        for step in self.steps:
            deps = (
                f" (depends on: {', '.join(step.dependencies)})"
                if step.dependencies
                else ""
            )
            status = f"[{step.state.value}]"
            lines.append(f"  {status:12} {step.name}{deps}")

        return "\n".join(lines)


class WorkflowBuilder:
    """
    Fluent builder for creating workflows.

    Example:
        ```python
        workflow = (
            WorkflowBuilder("my_workflow")
            .add(CodeAgent(), "Generate code")
            .add(ReviewAgent(), "Review code", depends_on=["step_1"])
            .parallel([
                (TestAgent(), "Write unit tests"),
                (DocAgent(), "Write docs"),
            ], depends_on=["step_2"])
            .build()
        )
        ```
    """

    def __init__(self, name: str, description: str = ""):
        """Initialize the workflow builder with an empty workflow."""
        self._workflow = Workflow(name, description)
        self._step_count = 0

    def add(
        self,
        agent: Agent,
        task: str,
        name: Optional[str] = None,
        depends_on: Optional[List[str]] = None,
        **kwargs,
    ) -> WorkflowBuilder:
        """Add a step."""
        self._step_count += 1
        step_name = name or f"step_{self._step_count}"
        self._workflow.add_step(
            agent, task, name=step_name, depends_on=depends_on, **kwargs
        )
        return self

    def parallel(
        self,
        steps: List[tuple],
        depends_on: Optional[List[str]] = None,
    ) -> WorkflowBuilder:
        """Add multiple steps that can run in parallel."""
        for agent, task in steps:
            self._step_count += 1
            self._workflow.add_step(
                agent, task, name=f"step_{self._step_count}", depends_on=depends_on
            )
        return self

    def build(self) -> Workflow:
        """Build and return the workflow."""
        return self._workflow
