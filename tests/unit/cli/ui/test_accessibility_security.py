from rich.console import Console

from aura_cli.cli.ui.accessibility import (
    AccessibilityChecker,
    AlternativeText,
    ColorContrast,
    FocusIndicator,
)
from aura_cli.cli.ui.constants import UIIcons
from aura_cli.cli.ui.security import evaluate_command_security


def test_unicode_icons_have_accessible_descriptions() -> None:
    assert AlternativeText.describe_icon(UIIcons.SUCCESS) == "sucesso"
    assert AlternativeText.describe_icon(UIIcons.ERROR) == "erro"
    assert AlternativeText.describe_icon(UIIcons.TOOL) == "ferramenta"


def test_color_contrast_accepts_rich_named_colors() -> None:
    assert ColorContrast.meets_wcag_aa("white", "black") is True
    assert ColorContrast.contrast_ratio("bright_green", "black") > 4.5


def test_focus_indicator_and_report_use_injected_console() -> None:
    console = Console(record=True, width=60)
    focus = FocusIndicator(console)
    focus.show_focus("prompt", "Entrada atual")
    checker = AccessibilityChecker()
    checker.check_focus_indicator(False)
    console.print(checker.render_report(console))
    output = console.export_text(clear=False)

    assert "Entrada atual" in output
    assert "Relatório de acessibilidade" in output
    assert "avisos" in output
    assert "warnings" not in output


def test_security_warning_is_conservative_and_width_aware() -> None:
    safe, safe_warning = evaluate_command_security("ls -la", console_width=60)
    dangerous, warning = evaluate_command_security("rm -rf /tmp/a", console_width=60)

    assert safe is False
    assert safe_warning is None
    assert dangerous is True
    assert warning is not None

    console = Console(record=True, width=60)
    console.print(warning)
    output = console.export_text(clear=False)
    assert "Aviso de segurança" in output
    assert "Confirmação explícita necessária" in output
    assert "⚠" not in output
