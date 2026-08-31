from types import SimpleNamespace

from aura_cli.application.agents.ops_planning import (
    build_effective_ops_prompt,
    build_ops_planning_prompt,
    build_ops_workflow_blueprint,
    build_ops_workflow_result,
    render_delegation_context,
    select_ops_agent,
    valid_workflow_tasks,
)


def _task(task_type: str, description: str = "", **parameters):
    return SimpleNamespace(
        description=description,
        parameters={"type": task_type, **parameters},
    )


def test_delegation_context_is_bounded_and_effective_prompt_wraps_task() -> None:
    payload = {"primary_request": "inspect", "supporting_context": "x" * 1200}
    context = render_delegation_context(payload)
    prompt = build_effective_ops_prompt("run checks", payload)

    assert "primary_request: inspect" in context
    assert "x" * 1000 in context
    assert "x" * 1001 not in context
    assert prompt.startswith("[CHAT DELEGATION HANDOFF]")
    assert "Task to execute:\nrun checks" in prompt
    assert build_effective_ops_prompt("plain", None) == "plain"


def test_planning_prompt_carries_mode_payload_and_json_constraints() -> None:
    prompt = build_ops_planning_prompt("docker", {"primary_request": "inspect"})

    assert "**MODO ATUAL:** docker" in prompt
    assert "primary_request: inspect" in prompt
    assert '"mode": "docker"' in prompt
    assert "Retorne APENAS o JSON" in prompt


def test_planning_prompt_includes_workspace_diff() -> None:
    prompt = build_ops_planning_prompt(
        "git",
        workspace_diff="**WORKSPACE DIFF**\n- M app.py",
    )

    assert "WORKSPACE DIFF" in prompt
    assert "app.py" in prompt


def test_agent_routing_uses_only_available_specialists() -> None:
    git_task = _task("read_file", "check git branch")
    docker_task = _task("docker_ps")

    assert select_ops_agent(git_task, {"ops_git_agent"}) == "ops_git_agent"
    assert select_ops_agent(docker_task, {"ops_docker_agent"}) == "ops_docker_agent"
    assert select_ops_agent(git_task, {"ops_code_agent"}) == "ops_code_agent"


def test_workflow_validation_defaults_paths_and_filters_invalid_tasks() -> None:
    read = _task("read_file")
    find = _task("find_in_files", pattern="needle", path="src")
    invalid = _task("find_in_files", path="src")
    git_status = _task("git_status")
    docker_ps = _task("docker_ps", all=True)

    assert valid_workflow_tasks([read, find, invalid, git_status, docker_ps]) == [
        read,
        find,
        git_status,
        docker_ps,
    ]
    assert read.parameters["path"] == "."


def test_workflow_blueprint_routes_steps_and_preserves_dependencies() -> None:
    first = _task("git_status", "inspect git")
    first.id, first.dependencies = "one", []
    second = _task("docker_ps", "inspect containers")
    second.id, second.dependencies = "two", ["one"]
    plan = SimpleNamespace(tasks=[first, second])

    blueprint = build_ops_workflow_blueprint(
        plan,
        mode="general",
        prompt="inspect infrastructure",
        workflow_id="ops-1",
        available_agents={"ops_code_agent", "ops_git_agent", "ops_docker_agent"},
    )

    assert blueprint.workflow_id == "ops-1"
    assert [step.agent_id for step in blueprint.steps] == [
        "ops_git_agent",
        "ops_docker_agent",
    ]
    assert blueprint.steps[1].dependencies == ("one",)


def test_workflow_result_has_stable_artifact_shape() -> None:
    result = build_ops_workflow_result(
        prompt="inspect",
        model="model",
        mode="git",
        workflow_result={"status": "completed", "iterations": 2},
        context_summary="summary",
        tools_used=("git_status",),
        delegation_payload={"source": "chat"},
    )

    assert result["status"] == "completed"
    assert result["tools_used"] == ["git_status"]
    assert result["workflow_result"]["iterations"] == 2
    assert result["generated_files"] == []
