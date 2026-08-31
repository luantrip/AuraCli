"""Tests for AGI planner task routing and normalization helpers."""

from types import SimpleNamespace

from aura_cli.core.agi.planning import AgiPlanner


def _make_planner(tmp_path):
    return AgiPlanner(
        model="gpt-4o",
        project_root=tmp_path,
        agi_event_adapter=SimpleNamespace(emit_chat_message=lambda **kwargs: None),
        human_intervention_adapter=SimpleNamespace(
            request_confirmation=lambda **kwargs: True
        ),
        use_advanced_features=True,
    )


def test_select_agent_for_task_prefers_requested_agent(tmp_path):
    """The planner should honor an explicit agent when that agent exists."""
    planner = _make_planner(tmp_path)
    task = SimpleNamespace(parameters={"type": "read_file", "agent": "review_agent"})
    orchestrator = SimpleNamespace(
        agents={"review_agent": object(), "code_agent": object()}
    )

    assert planner.select_agent_for_task(task, orchestrator) == "review_agent"


def test_select_agent_for_task_routes_code_analysis_to_review_agent(tmp_path):
    """Analyze-code tasks should prefer the review agent when available."""
    planner = _make_planner(tmp_path)
    task = SimpleNamespace(parameters={"type": "analyze_code"})
    orchestrator = SimpleNamespace(
        agents={"review_agent": object(), "code_agent": object()}
    )

    assert planner.select_agent_for_task(task, orchestrator) == "review_agent"


def test_normalize_task_params_preserves_selected_agent(tmp_path):
    """Normalization should carry the chosen agent into task parameters."""
    planner = _make_planner(tmp_path)

    params = planner.normalize_task_params(
        {"type": "read_file", "path": "README.md"},
        "code_agent",
    )

    assert params["path"].endswith("README.md")
    assert params["agent"] == "code_agent"


def test_select_agent_for_task_routes_refactoring_to_refactor_agent(tmp_path):
    """Refactoring tasks should prefer the refactor agent when available."""
    planner = _make_planner(tmp_path)
    task = SimpleNamespace(parameters={"type": "plan_refactoring"})
    orchestrator = SimpleNamespace(
        agents={"refactor_agent": object(), "code_agent": object()}
    )

    assert planner.select_agent_for_task(task, orchestrator) == "refactor_agent"


def test_select_agent_for_task_routes_tests_to_test_agent(tmp_path):
    """Test tasks should prefer the test agent when available."""
    planner = _make_planner(tmp_path)
    task = SimpleNamespace(parameters={"type": "run_tests"})
    orchestrator = SimpleNamespace(
        agents={"test_agent": object(), "code_agent": object()}
    )

    assert planner.select_agent_for_task(task, orchestrator) == "test_agent"


def test_allowed_task_types_include_specialized_agent_capabilities(tmp_path):
    """Planner allowlist should include the specialized agent task surface."""
    planner = _make_planner(tmp_path)

    assert "review_file" in planner.allowed_task_types
    assert "run_tests" in planner.allowed_task_types
    assert "plan_refactoring" in planner.allowed_task_types
