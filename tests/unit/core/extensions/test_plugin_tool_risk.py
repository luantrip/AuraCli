"""Security contracts for tools contributed by plugins."""

from unittest.mock import MagicMock, patch

from aura_cli.core.extensions.plugin_api import (
    AuraPlugin,
    PluginManager,
    PluginToolDescriptor,
)


class _Plugin(AuraPlugin):
    @property
    def name(self) -> str:
        return "sample"

    @property
    def version(self) -> str:
        return "1.0.0"


def test_plugin_with_callable_but_no_risk_descriptor_is_rejected() -> None:
    plugin = _Plugin()
    plugin.get_tools = lambda: {"unsafe": lambda: None}  # type: ignore[method-assign]

    assert PluginManager().register_plugin(plugin) is False


def test_plugin_descriptor_forwards_explicit_effect_and_risk() -> None:
    plugin = _Plugin()
    plugin.get_tools = lambda: {  # type: ignore[method-assign]
        "inspect": PluginToolDescriptor(
            function=lambda: "ok",
            effect="read_only",
            risk="low",
        )
    }
    registry = MagicMock()

    with patch(
        "aura_cli.core.service_registry.get_service_registry", return_value=registry
    ):
        assert PluginManager().register_plugin(plugin) is True

    registered = registry.register_tool.call_args
    assert registered.kwargs["effect"].value == "read_only"
    assert registered.kwargs["risk"].value == "low"
