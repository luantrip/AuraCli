"""Focused tests for the optional embedding subprocess lifecycle."""

from unittest.mock import Mock, patch

from aura_cli.cli.runtime import EmbeddingServerLifecycle


def test_start_reuses_process_already_bound_to_port() -> None:
    lifecycle = EmbeddingServerLifecycle()
    with (
        patch.object(lifecycle, "port_in_use", return_value=True),
        patch("aura_cli.cli.runtime.subprocess.Popen") as popen,
    ):
        assert lifecycle.start(8765) is None
    popen.assert_not_called()


def test_stop_terminates_owned_process_once() -> None:
    lifecycle = EmbeddingServerLifecycle()
    process = Mock()
    lifecycle._process = process

    lifecycle.stop()
    lifecycle.stop()

    process.terminate.assert_called_once_with()
    process.wait.assert_called_once_with(timeout=10)
