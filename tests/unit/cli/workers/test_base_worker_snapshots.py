from types import SimpleNamespace
from unittest.mock import Mock

from aura_cli.cli.workers.base_worker import BaseWorker


class SnapshotWorker(BaseWorker):
    def __init__(self, history):
        super().__init__(task_id="snapshot")
        self.context_manager = SimpleNamespace(conversation_history=history)
        self._notebook_service = Mock()
        self._notebook_service.create_snapshot.return_value = "notebooks/page-1.txt"
        self.last_snapshot_path = None
        self._last_notebook_snapshot = 0
        self._notebook_snapshot_interval = 5
        self.saved = 0

    def _save_worker_snapshot(self) -> None:
        if self._create_notebook_snapshot() is not None:
            self.saved += 1


def test_base_worker_creates_snapshot_through_notebook_adapter() -> None:
    history = [{"role": "user", "content": str(index)} for index in range(5)]
    worker = SnapshotWorker(history)

    worker._check_and_save_periodic_snapshot()

    assert worker.saved == 1
    assert worker._last_notebook_snapshot == 5
    assert worker.last_snapshot_path == "notebooks/page-1.txt"
    worker._notebook_service.create_snapshot.assert_called_once()


def test_base_worker_skips_short_or_unchanged_history() -> None:
    worker = SnapshotWorker([{"role": "user", "content": "one"}])
    worker._check_and_save_periodic_snapshot()
    assert worker.saved == 0

    worker.context_manager.conversation_history *= 5
    worker._last_notebook_snapshot = 5
    worker._check_and_save_periodic_snapshot()
    assert worker.saved == 0
