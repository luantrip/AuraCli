"""Testes completos para workers."""


class TestWorkersExist:
    """Testes de existência de workers."""

    def test_agi_worker_import(self):
        """Testa importação do AGI Worker."""
        from aura_cli.cli.workers.agi_worker import AgiWorker

        assert AgiWorker is not None

    def test_ops_worker_import(self):
        """Testa importação do Ops Worker."""
        from aura_cli.cli.workers.ops_worker import OpsWorker

        assert OpsWorker is not None

    def test_workers_module_import(self):
        """Testa importação do módulo workers."""
        from aura_cli.cli import workers

        assert workers is not None
        assert hasattr(workers, "AgiWorker")
        assert hasattr(workers, "OpsWorker")
