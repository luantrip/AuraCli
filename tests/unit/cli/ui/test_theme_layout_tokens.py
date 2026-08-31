from aura_cli.cli.ui.theme_manager import ThemeManager


def test_theme_layout_tokens_normalize_valid_values() -> None:
    tokens = ThemeManager._normalize_layout_tokens(
        {
            "panel_padding": [2, 4],
            "chat_padding": [0, 3],
            "chat_margin": [0, 1, 2, 0],
            "chat_width_ratio": 0.72,
            "custom_gap": 2,
        }
    )

    assert tokens["panel_padding"] == [2, 4]
    assert tokens["chat_padding"] == [0, 3]
    assert tokens["chat_margin"] == [0, 1, 2, 0]
    assert tokens["chat_width_ratio"] == 0.72
    assert tokens["custom_gap"] == 2


def test_theme_layout_tokens_reject_malformed_geometry_and_clamp_ratio() -> None:
    tokens = ThemeManager._normalize_layout_tokens(
        {
            "panel_padding": [1],
            "chat_padding": ["bad", 2],
            "chat_margin": [0, 0, 1],
            "chat_width_ratio": 1.7,
        }
    )

    assert tokens["panel_padding"] == [1, 3]
    assert tokens["chat_padding"] == [1, 2]
    assert tokens["chat_margin"] == [0, 0, 1, 0]
    assert tokens["chat_width_ratio"] == 1.0
