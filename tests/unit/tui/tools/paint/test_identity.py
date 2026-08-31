"""Identity and entrypoint contracts for AuraPaint."""

from aura_cli.tui.tools.paint import AURA_PAINT_NAME, LEGACY_PROJECT_NAME
from aura_cli.tui.tools.paint.args import get_help_text
from aura_cli.tui.tools.paint.paint import AuraPaint, Paint


def test_aurapaint_is_canonical_with_legacy_alias() -> None:
    assert AURA_PAINT_NAME == "AuraPaint"
    assert LEGACY_PROJECT_NAME == "Textual Paint"
    assert AuraPaint.__name__ == "AuraPaint"
    assert Paint is AuraPaint
    assert AuraPaint.TITLE == "AuraPaint"


def test_aurapaint_cli_uses_native_entrypoint_name() -> None:
    help_text = get_help_text()

    assert "aura-paint" in help_text
    assert "textual-paint" not in help_text
