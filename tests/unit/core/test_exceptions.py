"""
Tests for structured exceptions.
"""

import pytest

from aura_cli.core.exceptions import (
    APIKeyError,
    AuraError,
    ModelNotFoundError,
    OperationCancelled,
    RateLimitError,
    SecurityError,
    ThreadError,
    ToolExecutionError,
    ValidationError,
)


class TestAuraError:
    def test_base_error_creation(self):
        exc = AuraError("Something went wrong")
        assert str(exc) == "Something went wrong"
        assert exc.context == {}

    def test_error_with_details_and_context(self):
        exc = AuraError("Error", details="More info", context={"file": "test.py"})
        assert str(exc) == "Error: More info"
        assert exc.context == {"file": "test.py"}

    def test_to_dict(self):
        exc = AuraError("Msg", details="Det")
        data = exc.to_dict()
        assert data["error_type"] == "AuraError"
        assert data["message"] == "Msg"
        assert data["details"] == "Det"


class TestOperationCancelled:
    def test_raise(self):
        with pytest.raises(OperationCancelled):
            raise OperationCancelled()


class TestRateLimitError:
    def test_creation(self):
        exc = RateLimitError(message="Too many requests", model="gpt-4", retry_after=60)
        assert exc.model == "gpt-4"
        assert exc.retry_after == 60
        assert "Too many requests" in str(exc)


class TestAPIKeyError:
    def test_creation(self):
        exc = APIKeyError("Invalid key", provider="openai")
        assert exc.provider == "openai"


class TestModelNotFoundError:
    def test_creation(self):
        exc = ModelNotFoundError("Not found", model="gpt-5")
        assert exc.model == "gpt-5"


class TestToolExecutionError:
    def test_creation(self):
        exc = ToolExecutionError("Failed", tool_name="ls", tool_params={"dir": "/root"})
        assert exc.tool_name == "ls"
        assert exc.tool_params == {"dir": "/root"}


class TestThreadError:
    def test_creation(self):
        exc = ThreadError("Thread died", thread_name="worker-1")
        assert exc.thread_name == "worker-1"


class TestValidationError:
    def test_creation(self):
        exc = ValidationError("Invalid email", field="email", value="bad-email")
        assert exc.field == "email"
        assert exc.value == "bad-email"


class TestSecurityError:
    def test_creation(self):
        exc = SecurityError(command="rm -rf /", reason="Dangerous")
        assert exc.command == "rm -rf /"
        assert exc.reason == "Dangerous"
        assert "Unsafe command blocked" in str(exc)
