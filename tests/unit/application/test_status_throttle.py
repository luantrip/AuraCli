import pytest

from aura_cli.application.agents import StatusThrottle


def test_throttle_accepts_first_and_interval_boundary() -> None:
    throttle = StatusThrottle(interval=0.5)

    assert throttle.allow(10.0) is True
    assert throttle.allow(10.49) is False
    assert throttle.allow(10.5) is True


def test_throttle_reset_allows_next_status() -> None:
    throttle = StatusThrottle(interval=10.0)
    assert throttle.allow(5.0) is True

    throttle.reset()

    assert throttle.allow(5.1) is True


def test_throttle_rejects_negative_interval() -> None:
    throttle = StatusThrottle(interval=-0.1)

    with pytest.raises(ValueError, match="cannot be negative"):
        throttle.allow(0.0)
