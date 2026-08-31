from pathlib import Path

from aura_cli.tui.app import AuraTUI


def test_every_theme_loads_shared_layout_last() -> None:
    for theme in ("nebula-dark", "macos-light"):
        paths = AuraTUI._get_css_paths(theme)
        assert len(paths) == 2
        assert Path(paths[0]).name in {"theme.tcss", "macos_light.tcss"}
        assert Path(paths[-1]).name == "layout.tcss"


def test_shared_layout_contains_responsive_surface_contract() -> None:
    layout = Path(AuraTUI._get_css_paths()[-1]).read_text(encoding="utf-8")

    for selector in (
        "#main_grid.drawer-overlay",
        "#left_panel.drawer-visible",
        "#analysis_panel_slot",
        "#main_grid.density-compact",
        "AuraFooter.compact",
    ):
        assert selector in layout
