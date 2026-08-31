"""ADK Workflow API — multi-step agent orchestration for plugins and extensions.

This module is the **public** workflow API.  Use it when building AuraCli
plugins or ADK-based agents.  Do *not* import from
``aura_cli.core.agents.agent_workflow`` directly — that module is an internal
implementation detail of the AGI engine.

Quick start
-----------
Build and run a two-step workflow::

    from aura_cli.adk.workflow import WorkflowBuilder, StepState

    async def my_agent_fn(task, **kwargs):
        ...

    builder = WorkflowBuilder("data-pipeline")
    builder.add_step("fetch", "Fetch data", my_agent_fn)
    builder.add_step("process", "Process data", my_agent_fn, dependencies=["fetch"])
    workflow = builder.build()

    result = await workflow.run()
    assert result.state == StepState.COMPLETED

Convenience helper
------------------
``create_workflow`` wraps ``WorkflowBuilder`` for simple cases::

    from aura_cli.adk.workflow import create_workflow

    wf = create_workflow(
        name="lint-and-test",
        steps=[
            {"id": "lint", "name": "Lint", "fn": run_lint},
            {"id": "test", "name": "Test", "fn": run_tests, "dependencies": ["lint"]},
        ],
    )
    result = await wf.run()
"""

from __future__ import annotations

from typing import Any, List

from aura_cli.application.agents.workflow import (
    StepState,
    Workflow,
    WorkflowBuilder,
    WorkflowResult,
    WorkflowState,
    WorkflowStep,
)

__all__ = [
    "StepState",
    "Workflow",
    "WorkflowBuilder",
    "WorkflowResult",
    "WorkflowState",
    "WorkflowStep",
    "create_workflow",
]


def create_workflow(
    name: str,
    steps: List[dict[str, Any]],
    description: str = "",
) -> Workflow:
    """Build a ``Workflow`` from a list of step dicts.

    Each step dict supports:
        id (str): Unique step identifier (required).
        name (str): Human-readable step name (required).
        fn (Callable): Async callable ``async (task, **kwargs) -> AgentResponse`` (required).
        dependencies (list[str]): IDs of steps that must finish first (default []).
        timeout (float | None): Per-step timeout in seconds (default None).
        retry (int): Number of retry attempts on failure (default 0).

    Args:
        name: Workflow name.
        steps: List of step configuration dicts.
        description: Optional workflow description.

    Returns:
        A configured ``Workflow`` ready to ``await workflow.run()``.

    Example::

        wf = create_workflow(
            name="deploy",
            steps=[
                {"id": "build",  "name": "Build",  "fn": build_fn},
                {"id": "test",   "name": "Test",   "fn": test_fn,  "dependencies": ["build"]},
                {"id": "deploy", "name": "Deploy", "fn": deploy_fn, "dependencies": ["test"]},
            ],
        )
    """
    builder = WorkflowBuilder(name, description=description)
    for step in steps:
        builder.add(
            agent=step["fn"],
            task=step.get("task", step["name"]),
            name=step["id"],
            depends_on=step.get("dependencies", []) or None,
        )
    return builder.build()
