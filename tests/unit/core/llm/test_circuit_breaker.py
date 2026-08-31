"""
Tests for Circuit Breaker.

Tests the circuit breaker pattern implementation for LLM API calls:
- State transitions (CLOSED → OPEN → HALF_OPEN → CLOSED)
- Failure threshold enforcement
- Cooldown period
- Success threshold in HALF_OPEN state
- Thread safety
"""

import time
from unittest.mock import Mock

import pytest

from aura_cli.core.llm.circuit_breaker import CircuitBreaker, CircuitState


@pytest.fixture
def breaker():
    """Create circuit breaker with short timeouts for testing."""
    return CircuitBreaker(
        failure_threshold=3, cooldown_seconds=1.0, success_threshold=2
    )


class TestStateTransitions:
    """Test circuit breaker state machine."""

    def test_initial_state_closed(self, breaker):
        """Should start in CLOSED state."""
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_closed_to_open_on_threshold(self, breaker):
        """Should transition to OPEN after failure threshold."""
        failing_func = Mock(side_effect=RuntimeError("API error"))

        # First 2 failures keep circuit CLOSED
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.CLOSED

        # Third failure opens circuit
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.OPEN

    def test_open_to_half_open_after_cooldown(self, breaker):
        """Should transition to HALF_OPEN after cooldown period."""
        failing_func = Mock(side_effect=RuntimeError("API error"))

        # Open the circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.OPEN

        # Wait for cooldown
        time.sleep(1.1)

        # Next call should transition to HALF_OPEN
        success_func = Mock(return_value="success")
        result = breaker.call(success_func)
        assert result == "success"
        assert breaker.get_state() == CircuitState.HALF_OPEN

    def test_half_open_to_closed_on_success(self, breaker):
        """Should close circuit after success threshold in HALF_OPEN."""
        failing_func = Mock(side_effect=RuntimeError("API error"))
        success_func = Mock(return_value="success")

        # Open circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        # Wait and transition to HALF_OPEN
        time.sleep(1.1)
        breaker.call(success_func)
        assert breaker.get_state() == CircuitState.HALF_OPEN

        # Second success should close circuit
        breaker.call(success_func)
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.failure_count == 0

    def test_half_open_to_open_on_failure(self, breaker):
        """Should reopen circuit on failure in HALF_OPEN state."""
        failing_func = Mock(side_effect=RuntimeError("API error"))
        success_func = Mock(return_value="success")

        # Open circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        # Transition to HALF_OPEN
        time.sleep(1.1)
        breaker.call(success_func)
        assert breaker.get_state() == CircuitState.HALF_OPEN

        # Failure should reopen circuit
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.OPEN


class TestCallExecution:
    """Test function call execution through circuit breaker."""

    def test_call_success_in_closed_state(self, breaker):
        """Should execute function normally in CLOSED state."""
        func = Mock(return_value="result")
        result = breaker.call(func, "arg1", kwarg1="value1")

        assert result == "result"
        func.assert_called_once_with("arg1", kwarg1="value1")
        assert breaker.get_state() == CircuitState.CLOSED

    def test_call_blocked_in_open_state(self, breaker):
        """Should block calls in OPEN state."""
        failing_func = Mock(side_effect=RuntimeError("API error"))

        # Open circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        # Immediate call should be blocked
        with pytest.raises(Exception, match="Circuit breaker is OPEN"):
            breaker.call(Mock(return_value="success"))

    def test_call_allowed_in_half_open_state(self, breaker):
        """Should allow test calls in HALF_OPEN state."""
        failing_func = Mock(side_effect=RuntimeError("API error"))
        success_func = Mock(return_value="success")

        # Open circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        # Wait for cooldown
        time.sleep(1.1)

        # Should allow call in HALF_OPEN
        result = breaker.call(success_func)
        assert result == "success"


class TestFailureHandling:
    """Test failure counting and handling."""

    def test_failure_count_increments(self, breaker):
        """Should increment failure count on each failure."""
        failing_func = Mock(side_effect=RuntimeError("API error"))

        assert breaker.failure_count == 0

        with pytest.raises(RuntimeError):
            breaker.call(failing_func)
        assert breaker.failure_count == 1

        with pytest.raises(RuntimeError):
            breaker.call(failing_func)
        assert breaker.failure_count == 2

    def test_failure_count_resets_on_success(self, breaker):
        """Should reset failure count on success in CLOSED state."""
        failing_func = Mock(side_effect=RuntimeError("API error"))
        success_func = Mock(return_value="success")

        # Record some failures
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)
        assert breaker.failure_count == 2

        # Success should reset count
        breaker.call(success_func)
        assert breaker.failure_count == 0


class TestManagement:
    """Test management and introspection functions."""

    def test_reset_to_closed_state(self, breaker):
        """Should reset to CLOSED state with cleared counters."""
        failing_func = Mock(side_effect=RuntimeError("API error"))

        # Open circuit
        for _ in range(3):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.OPEN

        # Reset
        breaker.reset()
        assert breaker.get_state() == CircuitState.CLOSED
        assert breaker.failure_count == 0
        assert breaker.success_count == 0
        assert breaker.last_failure_time is None

    def test_get_stats_reflects_state(self, breaker):
        """Should return accurate statistics."""
        failing_func = Mock(side_effect=RuntimeError("API error"))

        # Initial stats
        stats = breaker.get_stats()
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0

        # After failures
        for _ in range(2):
            with pytest.raises(RuntimeError):
                breaker.call(failing_func)

        stats = breaker.get_stats()
        assert stats["failure_count"] == 2
        assert stats["last_failure_time"] is not None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_failure_threshold(self):
        """Should open circuit immediately with zero threshold."""
        breaker = CircuitBreaker(failure_threshold=0, cooldown_seconds=1.0)
        failing_func = Mock(side_effect=RuntimeError("API error"))

        # With threshold=0, circuit opens immediately on first failure
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.OPEN

    def test_zero_cooldown(self):
        """Should handle zero cooldown period."""
        breaker = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.0)
        failing_func = Mock(side_effect=RuntimeError("API error"))
        success_func = Mock(return_value="success")

        # Open circuit
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)
        assert breaker.get_state() == CircuitState.OPEN

        # Should immediately allow HALF_OPEN
        result = breaker.call(success_func)
        assert result == "success"

    def test_high_success_threshold(self):
        """Should require multiple successes to close."""
        breaker = CircuitBreaker(
            failure_threshold=1, cooldown_seconds=0.1, success_threshold=5
        )
        failing_func = Mock(side_effect=RuntimeError("API error"))
        success_func = Mock(return_value="success")

        # Open circuit
        with pytest.raises(RuntimeError):
            breaker.call(failing_func)

        # Wait and transition to HALF_OPEN
        time.sleep(0.2)

        # Need 5 successes to close
        for _i in range(4):
            breaker.call(success_func)
            assert breaker.get_state() == CircuitState.HALF_OPEN

        # Fifth success closes circuit
        breaker.call(success_func)
        assert breaker.get_state() == CircuitState.CLOSED


class TestThreadSafety:
    """Test thread safety of circuit breaker."""

    def test_concurrent_calls_maintain_state(self, breaker):
        """Should maintain consistent state under concurrent access."""
        import threading

        success_func = Mock(return_value="success")
        results = []

        def worker():
            try:
                result = breaker.call(success_func)
                results.append(result)
            except Exception as e:
                results.append(str(e))

        # Run 10 concurrent calls
        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed in CLOSED state
        assert len(results) == 10
        assert all(r == "success" for r in results)
        assert breaker.get_state() == CircuitState.CLOSED
