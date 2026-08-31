"""Run the release checks that depend on the operator's environment.

The script never treats a headless runner as a screen-reader validation. Local
security and reliability checks are deterministic; terminal and screen-reader
checks report ``MANUAL`` until executed from a real interactive session.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Callable

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aura_cli.core.reliability import ProfileStore, RetryPolicy, retry_call
from aura_cli.core.reliability.faults import FaultInjector
from aura_cli.core.sessions.session_manager import SessionManager


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str
    details: str


def _check_profile_isolation() -> GateResult:
    with tempfile.TemporaryDirectory(prefix="aura-profile-gate-") as directory:
        store = ProfileStore(Path(directory) / "profiles")
        store.save("gate-a", {"PROFILE": "a"})
        store.save("gate-b", {"PROFILE": "b"})
        permissions = store.path_for("gate-a").stat().st_mode & 0o777
        isolated = store.load("gate-a") != store.load("gate-b")
        if permissions != 0o600 or not isolated:
            return GateResult("profile_isolation", "FAIL", "profile data is not isolated securely")
    return GateResult("profile_isolation", "PASS", "profiles are isolated with mode 0600")


def _check_fault_recovery() -> GateResult:
    injector = FaultInjector()
    injector.add("external-boundary", ConnectionError("transient"), times=2)
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        injector.check("external-boundary")
        return "recovered"

    result = retry_call(
        operation,
        policy=RetryPolicy(max_attempts=3, initial_delay=0, jitter=0),
    )
    if result != "recovered" or attempts != 3:
        return GateResult("fault_recovery", "FAIL", "retry did not recover the injected transient fault")
    return GateResult("fault_recovery", "PASS", "bounded retry recovered after two injected failures")


def _check_session_workspace_switch() -> GateResult:
    """Verify that a workspace switch cannot retain the previous session."""
    with tempfile.TemporaryDirectory(prefix="aura-session-gate-") as directory:
        root = Path(directory).resolve()
        first = root / "first"
        second = root / "second"
        first.mkdir()
        second.mkdir()
        manager = SessionManager(
            storage_path=root / "sessions",
            workspace_root=first,
        )
        session = manager.create_session("first-workspace")
        manager.set_workspace_root(second)
        storage_path = root / "sessions"
        session_path = storage_path / f"{session.id}.json"
        permissions_ok = (
            storage_path.stat().st_mode & 0o777 == 0o700
            and session_path.stat().st_mode & 0o777 == 0o600
        )
        if (
            manager.current_session is not None
            or manager.workspace_root != second.resolve()
            or manager.storage_path != storage_path.resolve()
            or not permissions_ok
        ):
            return GateResult(
                "session_workspace_switch",
                "FAIL",
                "workspace switch leaked session state or weakened storage isolation",
            )
    return GateResult(
        "session_workspace_switch",
        "PASS",
        "workspace switch cleared the active session and preserved private storage",
    )


def _check_terminal() -> GateResult:
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        return GateResult("interactive_terminal", "MANUAL", "run from a real interactive terminal")
    if os.environ.get("TERM", "dumb") == "dumb":
        return GateResult("interactive_terminal", "MANUAL", "terminal reports TERM=dumb")
    return GateResult("interactive_terminal", "PASS", f"interactive terminal detected ({os.environ['TERM']})")


def _check_screen_reader() -> GateResult:
    configured = os.environ.get("AURA_SCREEN_READER")
    if not configured:
        return GateResult(
            "screen_reader",
            "MANUAL",
            "set AURA_SCREEN_READER to the platform reader and run this gate interactively",
        )
    executable = shutil.which(configured)
    if executable is None:
        return GateResult("screen_reader", "FAIL", f"reader command is unavailable: {configured}")
    return GateResult("screen_reader", "PASS", f"reader command available: {executable}")


def run_checks() -> list[GateResult]:
    checks: list[Callable[[], GateResult]] = [
        _check_profile_isolation,
        _check_fault_recovery,
        _check_session_workspace_switch,
        _check_terminal,
        _check_screen_reader,
    ]
    return [check() for check in checks]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", dest="as_json")
    arguments = parser.parse_args()
    results = run_checks()
    if arguments.as_json:
        print(json.dumps([asdict(result) for result in results], indent=2))
    else:
        for result in results:
            print(f"[{result.status}] {result.name}: {result.details}")
    if any(result.status == "FAIL" for result in results):
        return 1
    if any(result.status == "MANUAL" for result in results):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
