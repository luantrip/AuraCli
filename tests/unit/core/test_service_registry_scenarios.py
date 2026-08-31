"""Scenario tests for ServiceRegistry runtime behavior."""

from unittest.mock import Mock, patch

import pytest

from aura_cli.core.service_registry import (
    ServiceRegistry,
    ToolCategory,
    ToolEffect,
    ToolRisk,
)


class TestServiceRegistryScenarios:
    """Covers cache, disabled tools and error-handler integration."""

    def test_execute_tool_uses_cache_on_repeated_calls(self):
        """Second call with same params should use cache."""
        registry = ServiceRegistry()
        fn = Mock(return_value={"ok": True})
        registry._register_tool(
            "cached_tool",
            ToolCategory.DEVELOPMENT,
            "cached test tool",
            fn,
            {},
            effect="read_only",
            cacheable=True,
        )

        first = registry.execute_tool("cached_tool", {"x": 1})
        second = registry.execute_tool("cached_tool", {"x": 1})

        assert first == {"ok": True}
        assert second == {"ok": True}
        fn.assert_called_once()
        assert registry.tools["cached_tool"].usage_count == 1

    def test_mutating_tool_never_uses_cache(self):
        """Repeated mutations must always invoke their implementation."""
        registry = ServiceRegistry()
        fn = Mock(side_effect=["first", "second"])
        registry._register_tool(
            "write_something",
            ToolCategory.FILE_SYSTEM,
            "mutating test tool",
            fn,
            {},
            effect="mutating",
        )

        assert registry.execute_tool("write_something", {"value": 1}) == "first"
        assert registry.execute_tool("write_something", {"value": 1}) == "second"
        assert fn.call_count == 2

    def test_public_registration_requires_effect_metadata(self):
        registry = ServiceRegistry()
        registry.register_tool(
            "plugin_read",
            ToolCategory.DEVELOPMENT,
            "plugin tool",
            Mock(return_value="ok"),
            {},
            effect=ToolEffect.READ_ONLY,
            risk=ToolRisk.LOW,
        )

        assert registry.tools["plugin_read"].effect == "read_only"

    def test_mutating_tool_cannot_enable_cache(self):
        registry = ServiceRegistry()

        with pytest.raises(ValueError, match="Mutating tools cannot be cacheable"):
            registry.register_tool(
                "unsafe_plugin",
                ToolCategory.DEVELOPMENT,
                "unsafe plugin tool",
                Mock(),
                {},
                effect=ToolEffect.MUTATING,
                risk=ToolRisk.HIGH,
                cacheable=True,
            )

    def test_execute_tool_returns_none_when_tool_is_disabled(self):
        """Disabled tools must not execute."""
        registry = ServiceRegistry()
        fn = Mock(return_value="should_not_run")
        registry._register_tool(
            "disabled_tool",
            ToolCategory.DEVELOPMENT,
            "disabled tool",
            fn,
            {},
        )
        registry.tools["disabled_tool"].enabled = False

        result = registry.execute_tool("disabled_tool", {})
        assert result is None
        fn.assert_not_called()

    def test_execute_tool_reports_errors_to_error_handler(self):
        """Tool exceptions should be routed to centralized error handler."""
        registry = ServiceRegistry()
        failing = Mock(side_effect=RuntimeError("boom"))
        registry._register_tool(
            "failing_tool",
            ToolCategory.DEVELOPMENT,
            "failing tool",
            failing,
            {},
        )
        fake_handler = Mock()

        with patch(
            "aura_cli.core.error_handler.get_error_handler", return_value=fake_handler
        ):
            result = registry.execute_tool("failing_tool", {"a": 1})

        assert result is None
        assert registry.tools["failing_tool"].error_count == 1
        fake_handler.handle_error.assert_called_once()
