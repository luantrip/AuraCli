"""Contracts for infrastructure-neutral delegated-task observations."""

from aura_cli.application.agents.delegated_ports import ThreadObservation


def test_thread_observation_is_an_immutable_value() -> None:
    observation = ThreadObservation(status="running", alive=True)
    assert observation.status == "running"
    assert observation.alive is True
