from types import SimpleNamespace

from aura_cli.application.execution_feedback import LoadingState
from aura_cli.cli.ui.loading_states import LoadingState as CliLoadingState
from aura_cli.core.agi.execution import AgiExecutionEngine


class _DummyAdapter:
    def emit_chat_message(self, **kwargs):
        return None


def _make_engine():
    planner = SimpleNamespace(
        allowed_task_types=[
            "review_file",
            "run_tests",
            "plan_refactoring",
            "analyze_impact",
            "suggest_strategy",
        ],
        select_agent_for_task=lambda task, orchestrator: task.parameters.get(
            "agent", "code_agent"
        ),
    )
    worker = SimpleNamespace(
        headless=True,
        result_queue=SimpleNamespace(put=lambda value: None),
        task_id="task",
        status_queue=None,
        agi_event_adapter=_DummyAdapter(),
        api_keys={},
        model="gpt-4o",
        available_tools={},
    )
    return AgiExecutionEngine(
        agi_worker=worker,
        planner=planner,
        context_manager=None,
        validator=None,
        workflow_executor=None,
        orchestrator=SimpleNamespace(agents={"code_agent": object()}),
        git_manager=None,
        communication_manager=None,
        agent_memory=None,
    )


def test_validate_tasks_normalizes_specialized_task_parameters():
    engine = _make_engine()
    tasks = [
        SimpleNamespace(parameters={"type": "review_file", "path": "src/app.py"}),
        SimpleNamespace(parameters={"type": "run_tests", "path": "tests/unit"}),
        SimpleNamespace(
            parameters={
                "type": "plan_refactoring",
                "pattern": "old_name",
                "replacement": "new_name",
            }
        ),
        SimpleNamespace(parameters={"type": "analyze_impact", "path": "src/app.py"}),
        SimpleNamespace(parameters={"type": "suggest_strategy", "pattern": "legacy"}),
    ]

    valid_tasks = engine._validate_tasks(tasks)

    assert len(valid_tasks) == 5
    assert valid_tasks[0].parameters["file_path"] == "src/app.py"
    assert valid_tasks[1].parameters["test_path"] == "tests/unit"
    assert valid_tasks[2].parameters["scope"] == "."
    assert valid_tasks[3].parameters["file_path"] == "src/app.py"
    assert valid_tasks[4].parameters["scope"] == "."


def test_configure_environment_supports_openrouter_key():
    engine = _make_engine()
    engine.worker.api_keys = {"OPENROUTER_API_KEY": "or-key"}
    engine.api_keys = engine.worker.api_keys
    engine.worker.model = "openrouter/meta-llama/llama-3.3-70b-instruct:free"
    engine.model = engine.worker.model

    api_key, actual_model = engine._configure_environment()

    assert api_key == "or-key"
    assert actual_model.startswith("openrouter/")


def test_configure_environment_supports_nvidia_key():
    engine = _make_engine()
    engine.worker.api_keys = {"NVIDIA_API_KEY": "nv-key"}
    engine.api_keys = engine.worker.api_keys
    engine.worker.model = "openai/nvidia/llama-3.3-nemotron-super-49b-v1"
    engine.model = engine.worker.model

    api_key, actual_model = engine._configure_environment()

    assert api_key == "nv-key"
    assert "nemotron" in actual_model


def test_build_final_result_payload_includes_tools_and_generated_files():
    engine = _make_engine()
    engine.context_manager = SimpleNamespace(tools_used=["read_file", "write_file"])
    engine.worker.generated_files = ["src/auth.py", "tests/test_auth.py"]
    engine.worker.edited_files = ["src/session.py"]
    engine.worker.analyzed_files = ["README.md"]

    result = engine._build_final_result_payload({"status": "completed"})

    assert result["tools_used"] == ["read_file", "write_file"]
    assert result["generated_files"] == ["src/auth.py", "tests/test_auth.py"]
    assert result["edited_files"] == ["src/session.py"]
    assert result["analyzed_files"] == ["README.md"]
    assert result["files_touched"] == [
        "src/auth.py",
        "tests/test_auth.py",
        "src/session.py",
        "README.md",
    ]


def test_extract_file_artifacts_classifies_agi_files():
    engine = _make_engine()
    engine.worker.generated_files = []
    engine.worker.edited_files = []
    engine.worker.analyzed_files = []

    engine._extract_file_artifacts('calling write_file with {"path": "src/auth.py"}')
    engine._extract_file_artifacts('calling edit_file with {"path": "src/session.py"}')
    engine._extract_file_artifacts('calling read_file with {"path": "README.md"}')

    assert engine.worker.generated_files == ["src/auth.py"]
    assert engine.worker.edited_files == ["src/session.py"]
    assert engine.worker.analyzed_files == ["README.md"]


def test_record_structured_task_artifacts_classifies_agi_workflow_files():
    engine = _make_engine()
    engine.worker.generated_files = []
    engine.worker.edited_files = []
    engine.worker.analyzed_files = []

    engine._record_structured_task_artifacts(
        {"type": "write_file", "path": "src/auth.py"}
    )
    engine._record_structured_task_artifacts(
        {"type": "edit_file", "path": "src/session.py"}
    )
    engine._record_structured_task_artifacts(
        {"type": "review_file", "file_path": "README.md"}
    )

    assert engine.worker.generated_files == ["src/auth.py"]
    assert engine.worker.edited_files == ["src/session.py"]
    assert engine.worker.analyzed_files == ["README.md"]


def test_build_instrumented_tools_records_real_tool_args():
    engine = _make_engine()
    engine.worker.generated_files = []
    engine.worker.edited_files = []
    engine.worker.analyzed_files = []

    def fake_write_file(path: str, content: str) -> str:
        return f"wrote {path}"

    wrapped = engine._build_instrumented_tools({"write_file": fake_write_file})
    result = wrapped["write_file"](path="src/auth.py", content="x")

    assert result == "wrote src/auth.py"
    assert engine.worker.generated_files == ["src/auth.py"]


def test_loading_state_contract_is_shared_with_cli_adapter():
    assert CliLoadingState is LoadingState


def test_execution_engine_defaults_to_headless_feedback_ports():
    engine = _make_engine()

    assert engine.progress_factory is None
    assert engine.publish_progress is None
    assert engine.publish_status is None
    with engine.tool_panel_context_factory(task_id=None, task_description="test"):
        pass
