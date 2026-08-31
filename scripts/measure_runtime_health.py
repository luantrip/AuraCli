#!/usr/bin/env python3
"""Measure deterministic runtime-health workloads from checked-in fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from aura_cli.application.presentation.visual_acceptance import run_visual_scenario
from aura_cli.core.ops_tools.monitoring.performance_monitor import PerformanceMonitor
from aura_cli.core.sessions.session_manager import Session, SessionManager

ROOT = Path(__file__).resolve().parents[1]
SCENARIO_PATH = ROOT / "tests/fixtures/visual_system/scenarios.json"


def _load_scenarios() -> dict[str, list[dict[str, Any]]]:
    document = json.loads(SCENARIO_PATH.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("visual scenarios root must be a mapping")
    scenarios: dict[str, list[dict[str, Any]]] = {}
    for name, events in document.items():
        if not isinstance(name, str) or not isinstance(events, list):
            raise ValueError("visual scenarios must map names to event lists")
        if not all(isinstance(event, dict) for event in events):
            raise ValueError(f"scenario {name!r} contains a non-mapping event")
        scenarios[name] = events
    return scenarios


def _measure_visual_replay(
    scenarios: dict[str, list[dict[str, Any]]], iterations: int
) -> dict[str, Any]:
    events_per_iteration = sum(len(events) for events in scenarios.values())
    frames = 0
    started = time.perf_counter()
    for _ in range(iterations):
        for events in scenarios.values():
            frames += len(
                run_visual_scenario(
                    events,
                    viewports=((80, 24), (160, 40)),
                    focused_task_id=None,
                    app_focused=True,
                )
            )
    elapsed = time.perf_counter() - started
    return {
        "iterations": iterations,
        "scenario_count": len(scenarios),
        "events_per_iteration": events_per_iteration,
        "frames": frames,
        "duration_ms": round(elapsed * 1000, 3),
        "frames_per_second": round(frames / elapsed, 3) if elapsed else 0.0,
    }


def _fixture_session_messages(
    scenarios: dict[str, list[dict[str, Any]]], repeats: int
) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = []
    for _ in range(repeats):
        for scenario_name, events in scenarios.items():
            for index, event in enumerate(events):
                messages.append(
                    {
                        "role": "user" if index % 2 == 0 else "assistant",
                        "content": json.dumps(
                            event, ensure_ascii=False, sort_keys=True
                        ),
                        "metadata": {"scenario": scenario_name},
                    }
                )
    return messages


def _measure_session_round_trip(
    scenarios: dict[str, list[dict[str, Any]]], repeats: int
) -> dict[str, Any]:
    messages = _fixture_session_messages(scenarios, repeats)
    session = Session(
        id="phase13-fixture",
        name="Phase 13 fixture session",
        created_at="2026-08-26T00:00:00",
        updated_at="2026-08-26T00:00:00",
        conversation_history=messages,
        current_directory=str(ROOT),
        tags=["phase13", "fixture"],
    )
    with tempfile.TemporaryDirectory(prefix="auracli-phase13-") as directory:
        manager = SessionManager(storage_path=Path(directory))
        started = time.perf_counter()
        manager.save_session(session)
        restored = manager.load_session(session.id)
        elapsed = time.perf_counter() - started
        path = Path(directory) / f"{session.id}.json"
        if restored is None or len(restored.conversation_history) != len(messages):
            raise RuntimeError("session fixture round-trip changed message count")
        size_bytes = path.stat().st_size
    return {
        "message_repeats": repeats,
        "message_count": len(messages),
        "json_size_bytes": size_bytes,
        "round_trip_duration_ms": round(elapsed * 1000, 3),
    }


def _measure_system_sample() -> dict[str, Any]:
    samples: dict[str, Any] = {}
    for label, cpu_interval in (("default", 1.0), ("interactive", 0.0)):
        monitor = PerformanceMonitor()
        started = time.perf_counter()
        metrics = monitor.collect_system_metrics(cpu_interval=cpu_interval)
        elapsed = time.perf_counter() - started
        samples[label] = {
            "cpu_interval": cpu_interval,
            "duration_ms": round(elapsed * 1000, 3),
            "returned_sections": sorted(metrics),
            "recorded_points": len(monitor.metrics),
        }
    return samples


def measure(*, replay_iterations: int, session_repeats: int) -> dict[str, Any]:
    if replay_iterations <= 0 or session_repeats <= 0:
        raise ValueError("iterations and repeats must be positive")
    scenarios = _load_scenarios()
    return {
        "fixture": str(SCENARIO_PATH.relative_to(ROOT)),
        "visual_replay": _measure_visual_replay(scenarios, replay_iterations),
        "session_round_trip": _measure_session_round_trip(scenarios, session_repeats),
        "system_sample": _measure_system_sample(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--replay-iterations", type=int, default=100)
    parser.add_argument("--session-repeats", type=int, default=64)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = measure(
        replay_iterations=args.replay_iterations,
        session_repeats=args.session_repeats,
    )
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
