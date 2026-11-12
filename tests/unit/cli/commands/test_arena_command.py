"""Regression tests for the /arena command handler.

Previously /arena was fire-and-forget: it built an ArenaWorker, called
worker.start(), and returned a static string without tracking the thread or
wiring the worker to the event bus — so progress and the winner never surfaced
in the chat. These tests lock in the fixed behaviour.
"""

from unittest.mock import MagicMock, patch


class TestHandleArena:
    """Tests for handle_arena."""

    def _reset_module_thread(self):
        import aura_cli.cli.commands.arena as arena_mod

        arena_mod._arena_thread = None

    def test_arena_uses_worker_factory_and_tracks_thread(self):
        """handle_arena must create the worker via the tracked factory."""
        from aura_cli.cli.commands import arena

        self._reset_module_thread()

        fake_worker = MagicMock()
        fake_thread = MagicMock()
        fake_thread.is_alive.return_value = True

        with patch(
            "aura_cli.cli.commands.arena.create_arena_worker_thread",
            return_value=(fake_worker, fake_thread),
        ) as mock_factory:
            msg = arena.handle_arena("--quick resolver o bug")

            mock_factory.assert_called_once()
            # The parsed task and quick agent count must reach the factory.
            kwargs = mock_factory.call_args.kwargs
            assert kwargs["agents"] == 16
            assert "resolver o bug" in kwargs["task"]
            # Thread is tracked at module level (not fire-and-forget).
            assert arena._arena_thread is fake_thread
            assert msg is not None and "Arena" in msg

    def test_arena_blocks_double_launch(self):
        """A second /arena while one is running must be refused."""
        from aura_cli.cli.commands import arena

        self._reset_module_thread()

        running = MagicMock()
        running.is_alive.return_value = True
        arena._arena_thread = running

        with patch(
            "aura_cli.cli.commands.arena.create_arena_worker_thread"
        ) as mock_factory:
            msg = arena.handle_arena("outra tarefa")

            mock_factory.assert_not_called()
            assert "in progress" in msg.lower()

    def test_arena_parses_agents_and_seed(self):
        """--agents and --seed flags must be parsed and forwarded."""
        from aura_cli.cli.commands import arena

        self._reset_module_thread()

        with patch(
            "aura_cli.cli.commands.arena.create_arena_worker_thread",
            return_value=(MagicMock(), MagicMock()),
        ) as mock_factory:
            arena.handle_arena("--agents 8 --seed 42 projetar API")

            kwargs = mock_factory.call_args.kwargs
            assert kwargs["agents"] == 8
            assert kwargs["seed"] == 42
            assert "projetar API" in kwargs["task"]

    def test_arena_default_judge_is_heuristic(self):
        """Without --judge-llm, use_llm_judge must be False (safe default)."""
        from aura_cli.cli.commands import arena

        self._reset_module_thread()

        with patch(
            "aura_cli.cli.commands.arena.create_arena_worker_thread",
            return_value=(MagicMock(), MagicMock()),
        ) as mock_factory:
            msg = arena.handle_arena("--quick resolver bug")

            assert mock_factory.call_args.kwargs["use_llm_judge"] is False
            assert "heuristic" in msg

    def test_arena_judge_llm_flag_opts_in(self):
        """--judge-llm must set use_llm_judge=True."""
        from aura_cli.cli.commands import arena

        self._reset_module_thread()

        with patch(
            "aura_cli.cli.commands.arena.create_arena_worker_thread",
            return_value=(MagicMock(), MagicMock()),
        ) as mock_factory:
            msg = arena.handle_arena("--judge-llm --quick resolver bug")

            kwargs = mock_factory.call_args.kwargs
            assert kwargs["use_llm_judge"] is True
            assert "resolver bug" in kwargs["task"]
            assert "LLM" in msg


class TestArenaWorkerWiring:
    """The worker must be wired to the event bus (progress + winner surface)."""

    def test_worker_has_event_adapter(self, tmp_path):
        """ArenaWorker must initialise an AgiEventAdapter for its status queue."""
        from aura_cli.cli.workers.arena_worker import ArenaWorker

        worker = ArenaWorker("t", project_root=tmp_path, agents=4, seed=0)

        assert worker.agi_event_adapter is not None
        # The adapter must share the worker's status queue.
        assert worker.agi_event_adapter.status_queue is worker.status_queue

    def test_build_judge_default_is_baseline(self, tmp_path):
        """Default judge has no evaluator (deterministic rubric heuristic)."""
        from aura_cli.cli.workers.arena_worker import ArenaWorker

        worker = ArenaWorker("t", project_root=tmp_path, agents=4)
        judge = worker._build_judge()

        assert judge.evaluator is None

    def test_build_judge_llm_wires_evaluator(self, tmp_path):
        """use_llm_judge=True wires an evaluator that calls the executor."""
        from aura_cli.cli.workers.arena_worker import ArenaWorker

        calls = []

        def fake_executor(prompt, **kwargs):
            calls.append((prompt, kwargs))
            return '{"winner": "a001", "scores": {}}'

        worker = ArenaWorker(
            "t", project_root=tmp_path, agents=4,
            executor=fake_executor, use_llm_judge=True, model="m",
        )
        judge = worker._build_judge()

        assert judge.evaluator is not None
        judge.evaluator("prompt-x")
        assert calls and calls[0][1].get("model") == "m"


class TestScoreHardening:
    """Score.from_mapping must survive untrusted judge payloads."""

    def test_unknown_keys_ignored(self):
        from aura_cli.core.evaluation.models import Score

        s = Score.from_mapping({"correctness": 7, "overall": 99, "bogus": "x"})
        assert s.correctness == 7.0

    def test_non_numeric_falls_back_to_zero(self):
        from aura_cli.core.evaluation.models import Score

        s = Score.from_mapping({"clarity": None, "robustness": "abc"})
        assert s.clarity == 0.0
        assert s.robustness == 0.0

    def test_empty_mapping_is_default(self):
        from aura_cli.core.evaluation.models import Score

        assert Score.from_mapping({}) == Score()
        assert Score.from_mapping(None) == Score()


class TestArenaResume:
    """A completed/interrupted bracket must resume instead of restarting."""

    def test_resume_does_not_regenerate_solutions(self, tmp_path, monkeypatch):
        from aura_cli.application.artifacts import ArtifactLayout
        from aura_cli.cli.workers.arena_worker import ArenaWorker

        exec_calls = {"count": 0}

        def counting_executor(prompt, **kwargs):
            exec_calls["count"] += 1
            return f"solution-{exec_calls['count']}"

        # First full run generates solutions for all competitors.
        worker1 = ArenaWorker(
            "same-task", project_root=tmp_path, agents=4, seed=1,
            executor=counting_executor,
        )
        worker1._run_impl()
        first_run_calls = exec_calls["count"]
        assert first_run_calls == 4  # one solution per competitor

        arena_dir = ArtifactLayout(project_root=tmp_path).project("arena")
        assert (arena_dir / "arena.json").exists()

        # Second worker on the same task/dir must resume — the bracket is done,
        # so it starts fresh only if phase != done. Force an interrupted state
        # by truncating the bracket to a mid-tournament phase.
        import json

        state = json.loads((arena_dir / "arena.json").read_text())
        state["phase"] = "judge"
        # revive all agents to simulate an interrupted mid-run
        for agent in state["agents"].values():
            agent["alive"] = True
        (arena_dir / "arena.json").write_text(json.dumps(state))

        exec_calls["count"] = 0
        worker2 = ArenaWorker(
            "same-task", project_root=tmp_path, agents=4, seed=1,
            executor=counting_executor,
        )
        worker2._run_impl()
        # Solutions already present → executor must NOT be called again.
        assert exec_calls["count"] == 0
