#!/usr/bin/env python3
"""Run bounded Aura runtime scenarios with isolated state and redacted evidence."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any
import uuid

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / "bin" / "python"
STATE_ROOT = ROOT / ".aura" / "rea-study" / "campaign-runs"
SECRET_PATTERN = re.compile(
    r"(?i)(api[_ -]?key|authorization|bearer|token|secret|password)([=: ]+)([^\s,;]+)"
)
PROVIDER_KEYS = (
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GOOGLE_API_KEY",
    "OPENROUTER_API_KEY",
    "NVIDIA_API_KEY",
    "CEREBRAS_API_KEY",
    "GROQ_API_KEY",
)


@dataclass(frozen=True)
class Scenario:
    name: str
    arguments: tuple[str, ...]
    cloud: bool = False
    provider: str | None = None
    timeout_seconds: int = 45
    expected: tuple[str, ...] = ()
    stdin: str | None = None
    prepare: str | None = None


SCENARIOS = (
    Scenario("version", ("--version",)),
    Scenario("help", ("--help",)),
    Scenario("chat_help", ("chat", "--help")),
    Scenario("agi_help", ("agi", "--help")),
    Scenario("ops_help", ("ops", "--help")),
    Scenario("settings_help", ("settings", "--help")),
    Scenario("mcp_help", ("--mcp", "--help")),
    Scenario(
        "mcp_stdio",
        ("--mcp",),
        timeout_seconds=30,
        expected=("protocolVersion", '"tools"'),
        stdin=(
            '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}\n'
            '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}\n'
        ),
    ),
    Scenario(
        "resume_session",
        ("--resume", "__SESSION_ID__"),
        timeout_seconds=45,
        expected=("Sessão retomada",),
        prepare="resume",
    ),
    Scenario(
        "groq_chat",
        ("chat", "Responda apenas READY.", "--model", "groq/openai/gpt-oss-20b"),
        True,
        "GROQ_API_KEY",
        90,
        ("READY",),
    ),
    Scenario(
        "google_chat",
        ("chat", "Responda apenas READY.", "--model", "gemini/gemini-2.5-flash"),
        True,
        "GOOGLE_API_KEY",
        90,
        ("READY",),
    ),
    Scenario(
        "openrouter_free_chat",
        ("chat", "Responda apenas READY.", "--model", "openrouter/free"),
        True,
        "OPENROUTER_API_KEY",
        90,
        ("READY",),
    ),
    Scenario(
        "nvidia_chat",
        (
            "chat",
            "Responda apenas READY.",
            "--model",
            "nvidia/nemotron-3.5-lightning-30b-a3b",
        ),
        True,
        "NVIDIA_API_KEY",
        90,
        ("READY",),
    ),
    Scenario(
        "cerebras_chat",
        ("chat", "Responda apenas READY.", "--model", "cerebras/gpt-oss-120b"),
        True,
        "CEREBRAS_API_KEY",
        90,
        ("READY",),
    ),
)

MANUAL_ERROR_MARKERS = (
    "model not found",
    "notfounderror",
    "unauthorized",
    "authentication",
    "rate limit",
    "quota",
    "not configured",
)


def redact(value: str) -> str:
    value = SECRET_PATTERN.sub(r"\1\2<redacted>", value)
    for key in PROVIDER_KEYS:
        secret = os.environ.get(key)
        if secret:
            value = value.replace(secret, "<redacted>")
    return value


def _child_environment(scenario: Scenario, state_dir: Path) -> dict[str, str]:
    environment = dict(os.environ)
    environment.update(
        {
            "AURA_PROFILE": f"rea-study-{scenario.name}",
            "AURA_HOME": str(state_dir),
            "AURA_PROJECT_ROOT": str(ROOT),
            "AURA_USE_ADK_BRIDGE": "true",
            "LITELLM_LOCAL_MODEL_COST_MAP": "True",
        }
    )
    if scenario.cloud and scenario.provider:
        for provider_key in PROVIDER_KEYS:
            if provider_key != scenario.provider:
                environment.pop(provider_key, None)
    return environment


def _prepare_scenario(scenario: Scenario, state_dir: Path) -> dict[str, str]:
    """Create deterministic state required before launching a scenario."""
    if scenario.prepare != "resume":
        return {}
    from aura_cli.core.sessions.session_manager import SessionManager

    manager = SessionManager(
        storage_path=state_dir / "sessions",
        workspace_root=ROOT,
    )
    session = manager.create_session(
        "REA runtime resume",
        description="Controlled runtime resume fixture",
        tags=["rea-study", "runtime"],
    )
    session.add_message("user", "resume-fixture")
    manager.save_session(session)
    config_path = state_dir / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "default_model": "groq/openai/gpt-oss-20b",
                "api_keys": {"groq_api_key": "runtime-fixture"},
                "accessibility": {"enabled": False, "device": "auto"},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    config_path.chmod(0o600)
    return {"__SESSION_ID__": session.id}


def _classify_result(scenario: Scenario, returncode: int, output: str) -> str:
    if returncode == 0 and all(fragment in output for fragment in scenario.expected):
        return "passed"
    lowered = output.casefold()
    if scenario.cloud and any(marker in lowered for marker in MANUAL_ERROR_MARKERS):
        return "manual"
    return "failed"


def _run_interactive(
    arguments: tuple[str, ...], environment: dict[str, str], timeout: int
) -> tuple[int, str, str]:
    """Run the prompt-toolkit entrypoint through a real pseudo-terminal."""
    import pexpect

    child = pexpect.spawn(
        str(PYTHON),
        ["-m", "aura_cli.cli.main", *arguments],
        cwd=str(ROOT),
        env=environment,
        encoding="utf-8",
        timeout=timeout,
    )
    try:
        child.expect([pexpect.TIMEOUT, pexpect.EOF], timeout=8)
        if not child.isalive():
            return child.exitstatus or 0, child.before or "", ""
        child.sendline("/exit")
        child.sendeof()
        child.expect(pexpect.EOF)
    except pexpect.TIMEOUT:
        child.close(force=True)
        return 124, child.before or "", "interactive scenario timed out"
    output = child.before or ""
    child.close()
    return child.exitstatus or 0, output, ""


def run_scenario(scenario: Scenario, run_dir: Path) -> dict[str, Any]:
    state_dir = run_dir / "state" / scenario.name
    state_dir.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    if scenario.cloud and scenario.provider and not os.environ.get(scenario.provider):
        return {
            "name": scenario.name,
            "kind": "cloud",
            "status": "skipped",
            "reason": f"missing {scenario.provider}",
        }
    substitutions = _prepare_scenario(scenario, state_dir)
    arguments = tuple(substitutions.get(argument, argument) for argument in scenario.arguments)
    environment = _child_environment(scenario, state_dir)
    try:
        if scenario.prepare == "resume":
            returncode, raw_stdout, raw_stderr = _run_interactive(
                arguments, environment, scenario.timeout_seconds
            )
        else:
            completed = subprocess.run(
                [str(PYTHON), "-m", "aura_cli.cli.main", *arguments],
                cwd=ROOT,
                env=environment,
                capture_output=True,
                text=True,
                input=scenario.stdin,
                timeout=scenario.timeout_seconds,
                check=False,
            )
            returncode, raw_stdout, raw_stderr = (
                completed.returncode,
                completed.stdout,
                completed.stderr,
            )
        stdout = redact(raw_stdout)
        stderr = redact(raw_stderr)
        combined_output = f"{stdout}\n{stderr}"
        status = _classify_result(scenario, returncode, combined_output)
        return {
            "name": scenario.name,
            "kind": "cloud" if scenario.cloud else "offline",
            "status": status,
            "exit_code": returncode,
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "stdout": stdout[-12000:],
            "stderr": stderr[-12000:],
            "expected": list(scenario.expected),
            "artifacts": sorted(
                str(path.relative_to(state_dir))
                for path in state_dir.rglob("*")
                if path.is_file()
            ),
        }
    except subprocess.TimeoutExpired as error:
        return {
            "name": scenario.name,
            "kind": "cloud" if scenario.cloud else "offline",
            "status": "timeout",
            "duration_ms": round((time.perf_counter() - started) * 1000, 2),
            "stdout": redact((error.stdout or "")[-12000:]),
            "stderr": redact((error.stderr or "")[-12000:]),
        }


def run_campaign(iterations: int, selected: set[str] | None) -> dict[str, Any]:
    run_id = f"{time.strftime('%Y%m%dT%H%M%S')}-{uuid.uuid4().hex[:8]}"
    run_dir = STATE_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    scenarios = [scenario for scenario in SCENARIOS if not selected or scenario.name in selected]
    results: list[dict[str, Any]] = []
    for iteration in range(1, iterations + 1):
        for scenario in scenarios:
            result = run_scenario(scenario, run_dir / f"iteration-{iteration:03d}")
            result["iteration"] = iteration
            results.append(result)
    report = {
        "campaign_id": run_id,
        "root": str(run_dir),
        "iterations": iterations,
        "scenario_count": len(scenarios),
        "results": results,
    }
    (run_dir / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--scenario", action="append", dest="scenarios")
    parser.add_argument("--offline", action="store_true", help="Run only non-cloud scenarios.")
    parser.add_argument("--cloud-only", action="store_true", help="Run only cloud scenarios.")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()
    if args.list:
        for scenario in SCENARIOS:
            print(scenario.name)
        return 0
    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    if args.offline and args.cloud_only:
        parser.error("--offline and --cloud-only are mutually exclusive")
    selected = set(args.scenarios) if args.scenarios else None
    if args.offline:
        selected = {scenario.name for scenario in SCENARIOS if not scenario.cloud} if selected is None else {
            name for name in selected if not next(item for item in SCENARIOS if item.name == name).cloud
        }
    if args.cloud_only:
        selected = {scenario.name for scenario in SCENARIOS if scenario.cloud} if selected is None else {
            name for name in selected if next(item for item in SCENARIOS if item.name == name).cloud
        }
    report = run_campaign(args.iterations, selected)
    summary = [
        {
            "name": result["name"],
            "iteration": result["iteration"],
            "status": result["status"],
            "exit_code": result.get("exit_code"),
        }
        for result in report["results"]
    ]
    print(json.dumps({"campaign_id": report["campaign_id"], "results": summary}, indent=2))
    return 0 if all(item["status"] in {"passed", "manual", "skipped"} for item in report["results"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
