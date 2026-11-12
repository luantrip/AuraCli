"""Policies for conversational Ops execution results and memory records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import AgentConfig


@dataclass(frozen=True)
class OpsMemoryRecord:
    """Content and metadata ready for an agent-memory adapter."""

    key: str
    value: Any
    context: Mapping[str, Any]
    ttl: int | None = None


@dataclass(frozen=True)
class OpsProviderPolicy:
    """Provider-specific credential and LLM defaults required by Ops."""

    credential_name: str
    missing_credential_label: str
    drop_unsupported_params: bool = False
    temperature: float = 0.7
    max_tokens: int = 4096


@dataclass(frozen=True)
class OpsAgentSpec:
    """Stable identity and collaboration settings for an Ops specialist."""

    agent_id: str
    channel_id: str = "ops_channel"
    memory_limit: int = 10


def get_ops_agent_specs() -> tuple[OpsAgentSpec, ...]:
    """Return the native Ops team in deterministic registration order."""
    return tuple(
        OpsAgentSpec(agent_id)
        for agent_id in ("ops_code_agent", "ops_git_agent", "ops_docker_agent")
    )


def get_ops_provider_policy(provider: str) -> OpsProviderPolicy:
    """Resolve provider-independent setup data without reading credentials."""
    credential_names = {
        "gemini": "GOOGLE_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
        "gpt": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "nvidia": "NVIDIA_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "groq": "GROQ_API_KEY",
    }
    normalized = provider.casefold()
    credential_name = credential_names.get(normalized, "GOOGLE_API_KEY")
    return OpsProviderPolicy(
        credential_name=credential_name,
        missing_credential_label=(
            credential_name if normalized in credential_names else "API key"
        ),
        drop_unsupported_params=normalized == "gemini",
    )


def format_missing_ops_credential(policy: OpsProviderPolicy) -> str:
    """Build provider-neutral recovery guidance for a missing credential."""
    return f"{policy.missing_credential_label} not configured. Set it up with /settings"


def build_ops_system_prompt(mode: str, workspace_diff: str = "") -> str:
    """Build the backend-neutral operating contract for the Ops assistant."""
    return f"""You are Aura Ops, an experienced autonomous DevOps engineer operating within the Aura CLI ecosystem.

**MODE:** {mode}

{workspace_diff}

**GIT:**
- git_status() — repository status
- git_diff() — view changes
- git_diff_context() — status, patch and untracked files in the workspace
- git_log() — commit history
- git_commit(message) — create commit
- git_smart(command) — smart Git commands

**DOCKER:**
- docker_ps() — list containers
- docker_logs(container) — view logs
- docker_build() — build image
- docker_exec(container, command) — run command

**SYSTEM:**
- system_resources() — system resources
- check_service_health(port) — health check
- process_info(name) — process info
- run_shell_command(command) — run any shell command

**FILESYSTEM AND CODE:**
- read_file(path) — read file content
- write_file(path, content) — create/write files
- edit_file(path, changes) — edit existing files
- list_directory(path) — list directory content
- tree_view(path) — visualize directory structure
- find_in_files(pattern, path) — search text in files

**WORKFLOW:**
1. Use tools to collect real data — never assume
2. Analyze results and provide practical recommendations
3. Execute necessary actions with available tools
4. Finish with "TERMINATE"

**RULES:**
- Always use available tools instead of asking the user
- Technical, objective and direct tone
- If a tool fails, explain the error and propose an alternative
"""


def build_ops_agent_configs(
    *, system_message: str, llm_config: Mapping[str, Any]
) -> tuple[AgentConfig, AgentConfig]:
    """Build assistant and proxy specifications for a concrete agent backend."""
    return (
        AgentConfig(
            name="aura_ops",
            role="assistant",
            system_message=system_message,
            llm_config=dict(llm_config),
        ),
        AgentConfig(
            name="user_proxy",
            role="proxy",
            system_message="",
            llm_config={},
            max_consecutive_auto_reply=15,
            human_input_mode="NEVER",
        ),
    )


def is_ops_termination_message(message: Mapping[str, Any]) -> bool:
    """Return whether an agent message terminates the autonomous conversation."""
    return str(message.get("content", "")).rstrip().endswith("TERMINATE")


def build_plan_memory_record(
    task_plan: Any, *, effective_prompt: str, mode: str
) -> OpsMemoryRecord:
    """Build the stable memory representation of the currently executing plan."""
    return OpsMemoryRecord(
        key="current_plan",
        value={
            "plan_id": task_plan.plan_id,
            "description": task_plan.description,
            "mode": mode,
            "tasks_count": len(task_plan.tasks),
            "estimated_duration": task_plan.estimated_duration,
        },
        context={"prompt": effective_prompt, "mode": mode},
    )


def build_discovery_memory_record(
    message: Any, *, sender: str, mode: str, timestamp: float
) -> OpsMemoryRecord | None:
    """Select substantive operational discoveries worth retaining temporarily."""
    if not isinstance(message, Mapping):
        return None
    content = str(message.get("content", ""))
    keywords = (
        "encontrei",
        "descobri",
        "identifiquei",
        "analisei",
        "completed",
        "status",
        "health",
    )
    if len(content) <= 50 or not any(word in content.casefold() for word in keywords):
        return None
    return OpsMemoryRecord(
        key=f"discovery_{int(timestamp)}",
        value=content[:500],
        context={"sender": sender, "mode": mode, "timestamp": timestamp},
        ttl=3600,
    )


def build_ops_chat_result(
    *,
    prompt: str,
    model: str,
    mode: str,
    summary: Mapping[str, Any],
    context_summary: Any,
    delegation_payload: Mapping[str, Any] | None,
    workspace_diff: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the stable worker result emitted after conversational execution."""
    return {
        "status": "completed",
        "prompt": prompt,
        "model": model,
        "mode": mode,
        "tools_used": list(summary.get("tools_used", [])),
        "duration": summary.get("duration", 0),
        "generated_files": list(summary.get("generated_files", [])),
        "edited_files": list(summary.get("edited_files", [])),
        "analyzed_files": list(summary.get("analyzed_files", [])),
        "files_touched": list(summary.get("files_touched", [])),
        "context_summary": context_summary,
        "delegation_payload": delegation_payload,
        "workspace_diff": dict(workspace_diff or {}),
    }


__all__ = [
    "OpsAgentSpec",
    "OpsMemoryRecord",
    "OpsProviderPolicy",
    "build_discovery_memory_record",
    "build_ops_agent_configs",
    "build_ops_chat_result",
    "build_ops_system_prompt",
    "build_plan_memory_record",
    "format_missing_ops_credential",
    "get_ops_agent_specs",
    "get_ops_provider_policy",
    "is_ops_termination_message",
]
