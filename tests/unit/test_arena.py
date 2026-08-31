from aura_cli.core.arena.engine import ArenaEngine


def test_arena_persists_and_resumes(tmp_path):
    engine = ArenaEngine(tmp_path)
    state = engine.init(4, seed=3, task="choose a design")
    engine.record_solution("a001", "A")
    engine.record_match("a001", "a002", "a001")
    resumed = ArenaEngine(tmp_path)
    resumed.resume()
    assert resumed.state.run_id == state.run_id
    assert resumed.state.agents["a001"].solution == "A"
    assert resumed.state.agents["a001"].alive
