"""Testes para workers."""


class TestWorkers:
    """Testes para workers."""

    def test_agi_worker_imports(self):
        """Testa imports do AGI worker."""
        from aura_cli.cli.workers import agi_worker

        assert agi_worker is not None

    def test_ops_worker_imports(self):
        """Testa imports do Ops worker."""
        from aura_cli.cli.workers import ops_worker

        assert ops_worker is not None
