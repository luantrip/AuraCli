from unittest.mock import Mock, patch

from aura_cli.cli.ui.settings_modal import (
    GRAPHITE_COLORS,
    build_model_options,
    graphite_dialog_style,
    settings_summary,
)


def test_graphite_theme_removes_blue_dialog_default() -> None:
    style = graphite_dialog_style()
    text = repr(style.style_rules)
    assert GRAPHITE_COLORS["surface"] in text
    assert GRAPHITE_COLORS["background"] in text
    assert "radio-checked" in text
    assert "frame.border" in text
    assert "#0000ff" not in text.lower()


def test_model_options_put_active_model_first_and_group_stably() -> None:
    models = {
        "z": {"name": "Zeta", "provider": "openai"},
        "a": {"name": "Alpha", "provider": "google"},
    }
    options = build_model_options(models, "z")
    assert options[0].model_id == "z"
    assert options[0].label.startswith("●")
    assert "atual" in options[0].label


def test_settings_summary_contains_navigation_contract() -> None:
    summary = settings_summary(3, "Gemini", "grafite")
    assert "3/6 provedores" in summary
    assert "Esc voltar" in summary


def test_model_command_opens_graphite_catalog_with_current_model_first() -> None:
    application = Mock()
    application.run.return_value = None
    models = {
        "google/gemini": {"name": "Gemini", "provider": "google"},
        "openai/gpt": {"name": "GPT", "provider": "openai"},
    }

    with (
        patch("aura_cli.cli.commands.config.get_valid_models", return_value=models),
        patch(
            "prompt_toolkit.shortcuts.radiolist_dialog", return_value=application
        ) as dialog,
    ):
        from aura_cli.cli.commands.config import handle_model

        result = handle_model("openai/gpt")

    assert result == "openai/gpt"
    kwargs = dialog.call_args.kwargs
    assert kwargs["values"][0][0] == "openai/gpt"
    assert kwargs["values"][0][1].startswith("●")
    assert GRAPHITE_COLORS["surface"] in repr(kwargs["style"].style_rules)
