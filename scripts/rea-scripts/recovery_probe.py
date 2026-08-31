#!/usr/bin/env python3
"""Exercise deterministic retry, isolation, and failure classification paths."""

from __future__ import annotations

import json
import os
from pathlib import Path

from aura_cli.core.reliability import ProfileStore, RetryPolicy, retry_call
from aura_cli.core.reliability.faults import FaultInjector


def main() -> int:
    injector = FaultInjector()
    injector.add("provider", ConnectionError("transient"), times=2)
    attempts = 0

    def flaky_call() -> str:
        nonlocal attempts
        attempts += 1
        injector.check("provider")
        return "recovered"

    recovered = retry_call(
        flaky_call,
        policy=RetryPolicy(max_attempts=3, initial_delay=0, jitter=0),
    )
    assert recovered == "recovered"
    assert attempts == 3

    failed = FaultInjector()
    failed.add("permanent", RuntimeError("permanent"), times=3)
    failed_attempts = 0

    def permanent_call() -> None:
        nonlocal failed_attempts
        failed_attempts += 1
        failed.check("permanent")

    try:
        retry_call(
            permanent_call,
            policy=RetryPolicy(max_attempts=2, initial_delay=0, jitter=0),
        )
    except RuntimeError:
        pass
    else:
        raise AssertionError("permanent failure was not surfaced")
    assert failed_attempts == 2

    root = Path(os.environ.get("AURA_HOME", ".aura/rea-study-recovery"))
    profiles = ProfileStore(root / "profiles")
    profiles.save("one", {"provider": "groq"})
    profiles.save("two", {"provider": "cerebras"})
    assert profiles.load("one") != profiles.load("two")
    assert profiles.path_for("one").stat().st_mode & 0o777 == 0o600

    report = {
        "status": "READY",
        "transient_attempts": attempts,
        "permanent_attempts": failed_attempts,
        "profile_isolation": True,
        "recovery": recovered,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "recovery-report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print("RECOVERY_READY")
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
