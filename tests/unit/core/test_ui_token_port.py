"""Dependency-inversion contracts for presentation tokens."""

from aura_cli.core import ui_bridge


def test_core_tokens_start_with_standalone_fallbacks() -> None:
    ui_bridge.reset_ui_tokens()
    assert ui_bridge.UIIcons.SUCCESS == "[OK]"
    assert ui_bridge.UIStyles.ERROR == "red"


def test_adapter_can_register_dynamic_tokens() -> None:
    class Icons:
        SUCCESS = "yes"

    class Styles:
        ERROR = "danger"

    try:
        ui_bridge.configure_ui_tokens(icons=Icons, styles=Styles)
        assert ui_bridge.UIIcons.SUCCESS == "yes"
        assert ui_bridge.UIStyles.ERROR == "danger"
    finally:
        ui_bridge.reset_ui_tokens()


def test_ui_port_does_not_import_cli_adapter() -> None:
    source = ui_bridge.__file__
    assert source is not None
    with open(source, encoding="utf-8") as module_file:
        assert "aura_cli.cli" not in module_file.read()
