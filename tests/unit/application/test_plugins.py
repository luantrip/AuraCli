from aura_cli.application.extensions import (
    AuraPlugin,
    PluginCoordinator,
    PluginHook,
)


class Plugin(AuraPlugin):
    @property
    def name(self) -> str:
        return "plugin"

    @property
    def version(self) -> str:
        return "1.0"


def test_plugin_coordinator_registers_and_toggles_plugin() -> None:
    coordinator = PluginCoordinator(tool_registrar=lambda plugin: True)
    plugin = Plugin()

    assert coordinator.register_plugin(plugin) is True
    assert coordinator.disable_plugin("plugin") is True
    assert coordinator.is_plugin_enabled("plugin") is False
    assert coordinator.enable_plugin("plugin") is True
    assert coordinator.get_stats()["total_plugins"] == 1


def test_plugin_dependencies_must_already_be_registered() -> None:
    class Dependent(Plugin):
        @property
        def name(self) -> str:
            return "dependent"

        @property
        def dependencies(self) -> list[str]:
            return ["missing"]

    assert PluginCoordinator().register_plugin(Dependent()) is False


def test_cancelled_plugin_hook_stops_later_callbacks() -> None:
    calls: list[str] = []

    class HookPlugin(Plugin):
        @property
        def hooks(self):
            def cancel(context):
                calls.append("cancel")
                context.cancel()

            def later(context):
                calls.append("later")

            return {PluginHook.BEFORE_COMMAND: cancel}

    coordinator = PluginCoordinator()
    assert coordinator.register_plugin(HookPlugin()) is True
    coordinator.hooks[PluginHook.BEFORE_COMMAND].append(
        lambda context: calls.append("later")
    )

    coordinator.emit_hook(PluginHook.BEFORE_COMMAND)

    assert calls == ["cancel"]
