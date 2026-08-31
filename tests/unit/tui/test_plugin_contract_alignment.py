from aura_cli.application.extensions import AuraPlugin, PluginMetadata
from aura_cli.tui.plugin_manager import AuraTUIPluginBase
from aura_cli.tui.plugins.sdk import PluginInfo


class Plugin(AuraTUIPluginBase):
    PLUGIN_NAME = "aligned"

    def get_widgets(self):
        return {}

    def on_load(self) -> None:
        return None

    def on_unload(self) -> None:
        return None

    def on_app_ready(self) -> None:
        return None


def test_both_tui_plugin_surfaces_use_canonical_metadata() -> None:
    plugin = Plugin()
    assert isinstance(plugin, AuraPlugin)
    assert isinstance(plugin.metadata, PluginMetadata)
    assert isinstance(PluginInfo(name="widget"), PluginMetadata)


def test_tui_lifecycle_adapts_to_canonical_enable_contract() -> None:
    plugin = Plugin()
    plugin.disable()
    assert plugin.enabled is False
    plugin.enabled = True
    assert plugin.is_enabled is True


def test_widget_plugin_info_preserves_visual_tags() -> None:
    info = PluginInfo(name="widget", tags=["visual"])

    assert info.tags == ["visual"]
    assert info.to_dict()["tags"] == ["visual"]
