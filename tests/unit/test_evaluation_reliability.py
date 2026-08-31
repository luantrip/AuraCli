from __future__ import annotations

import json

import pytest

from aura_cli.core.evaluation.models import Candidate, Score
from aura_cli.core.evaluation.reporting import render_report, save_report
from aura_cli.core.evaluation.scheduler import RunScheduler, RunStatus
from aura_cli.core.evaluation.selection import blind_pool, select_best
from aura_cli.core.reliability.faults import FaultInjector
from aura_cli.core.reliability.idempotency import IdempotencyStore
from aura_cli.core.reliability.middleware import MiddlewareChain, Request, Response
from aura_cli.core.reliability.profiles import ProfileStore
from aura_cli.core.reliability.retry import RetryPolicy, async_retry_call, retry_call


def test_scheduler_persists_and_resumes_interrupted_runs(tmp_path):
    path = tmp_path / "runs.json"
    scheduler = RunScheduler(path)
    queued = scheduler.enqueue("task-1", {"mode": "arena"})
    assert scheduler.claim_next().run_id == queued.run_id
    recovered = scheduler.resume()
    assert [item.run_id for item in recovered] == [queued.run_id]
    assert scheduler.get(queued.run_id).status == RunStatus.PENDING

    restored = RunScheduler(path)
    claimed = restored.claim_next()
    assert claimed.task_id == "task-1"
    restored.complete(claimed.run_id, "result.json")
    assert restored.get(claimed.run_id).result_path == "result.json"


def test_selection_is_weighted_blind_and_reports_diversity(tmp_path):
    candidates = [
        Candidate("a", "alpha implementation", Score(correctness=1, completeness=0.5)),
        Candidate("b", "beta implementation with tests", Score(correctness=0.9, completeness=1)),
    ]
    report = select_best(candidates)
    assert report.winner_id == "b"
    assert report.diversity > 0
    assert blind_pool(candidates)[0]["id"] != "a"
    assert "Winner" in render_report(report)
    output = save_report(report, tmp_path / "report.json")
    assert output.exists() and output.with_suffix(".md").exists()
    assert json.loads(output.read_text())["winner_id"] == "b"


def test_profile_store_isolates_and_restricts_profiles(tmp_path):
    store = ProfileStore(tmp_path / "profiles")
    path = store.save("agent-1", {"API_KEY": "secret"})
    second = ProfileStore(tmp_path / "profiles")
    assert store.load("agent-1")["API_KEY"] == "secret"
    assert second.load("agent-1")["API_KEY"] == "secret"
    assert store.list_profiles() == ["agent-1"]
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(ValueError):
        store.save("../escape", {})


def test_profile_store_rejects_symlink_and_insecure_profile_changes(tmp_path):
    root = tmp_path / "profiles"
    store = ProfileStore(root)
    store.save("agent-1", {"API_KEY": "secret"})

    profile_file = root / "agent-1" / "profile.json"
    profile_file.chmod(0o644)
    with pytest.raises(PermissionError):
        store.load("agent-1")

    profile_file.chmod(0o600)
    profile_file.unlink()
    target = tmp_path / "outside.json"
    target.write_text('{"API_KEY": "outside"}', encoding="utf-8")
    profile_file.symlink_to(target)
    with pytest.raises(PermissionError):
        store.load("agent-1")


def test_retry_idempotency_middleware_and_faults(tmp_path):
    calls = {"count": 0}

    def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RuntimeError("temporary")
        return "ok"

    assert retry_call(flaky, policy=RetryPolicy(max_attempts=3, initial_delay=0)) == "ok"
    store = IdempotencyStore(tmp_path / "idempotency.json")
    value, cached = store.execute("key", lambda: {"count": 1})
    assert value == {"count": 1} and not cached
    assert store.execute("key", lambda: {"count": 2}) == ({"count": 1}, True)

    def transport(request):
        return Response(200, request.headers["X-Trace"])

    chain = MiddlewareChain(transport)
    chain.add(lambda request, next_call: next_call(Request(request.method, request.target, {**request.headers, "X-Trace": "trace"})))
    assert chain.send(Request("GET", "/health")).payload == "trace"

    injector = FaultInjector()
    injector.add("provider", RuntimeError("offline"))
    with pytest.raises(RuntimeError):
        injector.check("provider")
    injector.check("provider")


@pytest.mark.asyncio
async def test_async_retry_does_not_change_contract():
    state = {"count": 0}

    async def flaky():
        state["count"] += 1
        if state["count"] == 1:
            raise RuntimeError("temporary")
        return "done"

    assert await async_retry_call(flaky, policy=RetryPolicy(max_attempts=2, initial_delay=0)) == "done"
