"""Scenario tests for CoreToolDiscovery behavior.

These tests focus on runtime characteristics observed during architecture mapping:
- Domain registration failures should not crash discovery.
- Reflection-based registration intentionally caps callable exports.
"""

from types import SimpleNamespace
from unittest.mock import Mock, patch

from scripts.tool_discovery import CoreToolDiscovery


def _fn(*args, **kwargs):
    return {"ok": True, "args": args, "kwargs": kwargs}


class TestCoreToolDiscoveryScenarios:
    """Scenario coverage for resilient and bounded tool discovery."""

    def test_register_file_system_tools_swallow_registration_error(self):
        """A single registration failure should be logged, not raised."""
        discovery = CoreToolDiscovery()
        registry = Mock()
        registry._register_tool.side_effect = RuntimeError("registry unavailable")

        with patch("scripts.tool_discovery.logger.warning") as warn_log:
            discovery._register_file_system_tools(registry)

        warn_log.assert_called()
        assert discovery.tools_registered == 0

    def test_autocomplete_registration_is_capped_to_ten_functions_total(self):
        """Autocomplete discovery should register at most 5+5 callables."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        fake_generation = SimpleNamespace(**{f"gen_{i}": _fn for i in range(12)})
        fake_filtering = SimpleNamespace(**{f"flt_{i}": _fn for i in range(11)})

        import aura_cli.core.autocomplete as autocomplete_pkg

        with (
            patch.object(autocomplete_pkg, "generation", fake_generation),
            patch.object(autocomplete_pkg, "filtering", fake_filtering),
        ):
            discovery._register_autocomplete_tools(registry)

        # Implementation currently enforces [:5] per module.
        assert registry._register_tool.call_count == 10
        assert discovery.tools_registered == 10
