import pytest

from aura_cli.application.presentation.cli_visual import (
    CliDensity,
    cli_label,
    decide_cli_visual,
)


@pytest.mark.parametrize(
    ("width", "density", "preview", "columns"),
    [
        (60, CliDensity.COMPACT, 1, False),
        (80, CliDensity.NORMAL, 3, False),
        (100, CliDensity.NORMAL, 3, False),
        (120, CliDensity.WIDE, 6, True),
        (160, CliDensity.WIDE, 6, True),
    ],
)
def test_visual_acceptance_widths(width, density, preview, columns) -> None:
    plan = decide_cli_visual(width)
    assert plan.density is density
    assert plan.result_preview_lines == preview
    assert plan.dashboard_columns is columns


def test_shared_vocabulary() -> None:
    assert cli_label("operations") == "Operações"
    assert cli_label("parallel_work") == "Trabalho paralelo"


def test_unknown_vocabulary_is_explicit() -> None:
    with pytest.raises(ValueError):
        cli_label("tools")


def test_non_concrete_adapter_width_uses_safe_default() -> None:
    assert decide_cli_visual(object()).width == 80  # type: ignore[arg-type]
