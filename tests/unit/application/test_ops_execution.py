from types import SimpleNamespace

from aura_cli.application.agents.ops_execution import (
    build_discovery_memory_record,
    build_ops_agent_configs,
    build_ops_chat_result,
    build_ops_system_prompt,
    build_plan_memory_record,
    format_missing_ops_credential,
    get_ops_agent_specs,
    get_ops_provider_policy,
    is_ops_termination_message,
)


def test_plan_memory_record_captures_execution_context() -> None:
    plan = SimpleNamespace(
        plan_id="plan-1",
        description="Inspect repository",
        tasks=[object(), object()],
        estimated_duration=12.5,
    )

    record = build_plan_memory_record(plan, effective_prompt="inspect", mode="git")

    assert record.key == "current_plan"
    assert record.value["tasks_count"] == 2
    assert record.context == {"prompt": "inspect", "mode": "git"}


def test_ops_system_prompt_and_agent_specs_define_backend_neutral_contract() -> None:
    prompt = build_ops_system_prompt("docker")
    assistant, proxy = build_ops_agent_configs(
        system_message=prompt,
        llm_config={"model": "test-model", "temperature": 0.4},
    )

    assert "**MODO:** docker" in prompt
    assert "docker_ps()" in prompt
    assert prompt.rstrip().endswith("alternativa")
    assert assistant.name == "aura_ops"
    assert assistant.model == "test-model"
    assert assistant.temperature == 0.4
    assert proxy.name == "user_proxy"
    assert proxy.max_consecutive_auto_reply == 15
    assert proxy.human_input_mode == "NEVER"


def test_ops_system_prompt_includes_workspace_diff() -> None:
    prompt = build_ops_system_prompt("git", "**WORKSPACE DIFF**\n- M app.py")

    assert "WORKSPACE DIFF" in prompt
    assert "app.py" in prompt


def test_ops_termination_requires_terminal_marker_at_message_end() -> None:
    assert is_ops_termination_message({"content": "done TERMINATE   "}) is True
    assert is_ops_termination_message({"content": "TERMINATE then continue"}) is False
    assert is_ops_termination_message({}) is False


def test_ops_provider_policy_maps_credentials_and_llm_defaults() -> None:
    gemini = get_ops_provider_policy("GEMINI")
    nvidia = get_ops_provider_policy("nvidia")
    unknown = get_ops_provider_policy("custom")

    assert gemini.credential_name == "GOOGLE_API_KEY"
    assert gemini.drop_unsupported_params is True
    assert nvidia.credential_name == "NVIDIA_API_KEY"
    assert nvidia.temperature == 0.7
    assert nvidia.max_tokens == 4096
    assert unknown.credential_name == "GOOGLE_API_KEY"
    assert unknown.missing_credential_label == "API key"
    assert format_missing_ops_credential(unknown).startswith("API key não configurada")


def test_ops_agent_specs_define_deterministic_native_team() -> None:
    specs = get_ops_agent_specs()

    assert [spec.agent_id for spec in specs] == [
        "ops_code_agent",
        "ops_git_agent",
        "ops_docker_agent",
    ]
    assert {spec.channel_id for spec in specs} == {"ops_channel"}
    assert {spec.memory_limit for spec in specs} == {10}


def test_discovery_memory_record_filters_and_bounds_messages() -> None:
    assert (
        build_discovery_memory_record(
            {"content": "short status"}, sender="agent", mode="git", timestamp=10
        )
        is None
    )
    assert (
        build_discovery_memory_record(
            "plain message", sender="agent", mode="git", timestamp=10
        )
        is None
    )

    record = build_discovery_memory_record(
        {"content": "Identifiquei " + "x" * 600},
        sender="ops",
        mode="general",
        timestamp=10.9,
    )

    assert record is not None
    assert record.key == "discovery_10"
    assert len(record.value) == 500
    assert record.context["sender"] == "ops"
    assert record.ttl == 3600


def test_chat_result_copies_summary_collections() -> None:
    tools = ["git_status"]
    summary = {
        "tools_used": tools,
        "duration": 1.5,
        "generated_files": ["new.py"],
        "edited_files": [],
        "analyzed_files": ["README.md"],
        "files_touched": ["new.py", "README.md"],
    }

    result = build_ops_chat_result(
        prompt="inspect",
        model="model",
        mode="git",
        summary=summary,
        context_summary="context",
        delegation_payload=None,
    )

    tools.append("git_diff")
    assert result["tools_used"] == ["git_status"]
    assert result["duration"] == 1.5
    assert result["files_touched"] == ["new.py", "README.md"]
