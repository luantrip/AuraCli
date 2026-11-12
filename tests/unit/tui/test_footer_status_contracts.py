"""Footer as the single global status surface + English string contracts.

Contracts:
  1. AuraFooter is the only module-level status widget declared in the main
     TUI app compose (no second status bar sharing the footer role).
  2. Footer, status sidebar, and bridge have no Portuguese UI strings.
  3. status_message default and clear values are English ("Ready").
"""

from __future__ import annotations

from pathlib import Path
import re

PRODUCT = Path(__file__).resolve().parents[3] / "aura_cli"

# Characteristic Portuguese patterns that must not appear in the four
# primary TUI status/display files after the EN migration.
_PT_PATTERNS_FOOTER = ["Pronto", "preparando", "abrindo", "aberta", "retornando"]
_PT_PATTERNS_SIDEBAR = ["Sem Tarefas", "Tarefas Ativas", "NÃO CONFIGURADO"]
_PT_PATTERNS_BRIDGE = [
    "Aprovar nesta sessão",
    "Aprovar e salvar política",
    "Ação necessária",
    "Operação bloqueada",
]


class TestFooterEnglishStrings:
    def test_footer_no_portuguese(self) -> None:
        source = (PRODUCT / "tui" / "widgets" / "footer.py").read_text(encoding="utf-8")
        hits = [p for p in _PT_PATTERNS_FOOTER if p in source]
        assert hits == [], f"Portuguese strings in footer.py: {hits}"

    def test_footer_default_status_is_english(self) -> None:
        source = (PRODUCT / "tui" / "widgets" / "footer.py").read_text(encoding="utf-8")
        assert '"Ready"' in source, "footer default status_message must be 'Ready'"
        assert '"Pronto"' not in source, "old Portuguese default 'Pronto' must be gone"

    def test_footer_phase_labels_are_english(self) -> None:
        source = (PRODUCT / "tui" / "widgets" / "footer.py").read_text(encoding="utf-8")
        assert '"preparing"' in source
        assert '"completed"' in source


class TestStatusSidebarEnglishStrings:
    def test_sidebar_no_portuguese(self) -> None:
        source = (PRODUCT / "tui" / "widgets" / "status.py").read_text(encoding="utf-8")
        hits = [p for p in _PT_PATTERNS_SIDEBAR if p in source]
        assert hits == [], f"Portuguese strings in status.py: {hits}"

    def test_sidebar_nim_status_english(self) -> None:
        source = (PRODUCT / "tui" / "widgets" / "status.py").read_text(encoding="utf-8")
        assert '"READY"' in source
        assert '"NOT CONFIGURED"' in source


class TestBridgeEnglishStrings:
    def test_bridge_approval_dialog_no_portuguese(self) -> None:
        source = (PRODUCT / "tui" / "bridge.py").read_text(encoding="utf-8")
        hits = [p for p in _PT_PATTERNS_BRIDGE if p in source]
        assert hits == [], f"Portuguese strings in bridge.py: {hits}"


class TestFooterIsSingleGlobalStatusWidget:
    """AuraFooter is the one and only footer-role widget in the main app.

    The constraint: tui/app.py compose must yield exactly one AuraFooter and
    must not yield a second, parallel status bar widget that could disagree
    with the footer (the bug class that G3 addresses at the state level).
    """

    def _footer_yields_in_app(self) -> list[int]:
        """Return line numbers where AuraFooter is yielded in app.py."""
        source = (PRODUCT / "tui" / "app.py").read_text(encoding="utf-8")
        return [
            i + 1
            for i, line in enumerate(source.splitlines())
            if "yield AuraFooter" in line
        ]

    def test_exactly_one_footer_in_app_compose(self) -> None:
        lines = self._footer_yields_in_app()
        assert len(lines) == 1, (
            f"Expected exactly one 'yield AuraFooter' in app.py; found {len(lines)}: {lines}"
        )

    def test_no_second_global_status_bar_widget(self) -> None:
        """No other StatusBar-role widget is yielded at compose top-level."""
        source = (PRODUCT / "tui" / "app.py").read_text(encoding="utf-8")
        # MiniStatusBar or raw StatusBar at the top-level compose would be duplicating the footer.
        # These are legitimately used inside sub-tools (file_manager etc.) — not in the main compose.
        # Check the main compose body (between 'def compose' and the next 'def ').
        compose_match = re.search(
            r"def compose\(self\).*?(?=\n    def |\Z)", source, re.DOTALL
        )
        assert compose_match, "compose() not found in app.py"
        compose_body = compose_match.group(0)
        # A second 'StatusBar' or 'MiniStatusBar' yield in compose would be a violation
        second_status_bar = re.findall(
            r"yield\s+(?:StatusBar|MiniStatusBar)", compose_body
        )
        assert second_status_bar == [], (
            f"A second StatusBar was yielded in app.compose: {second_status_bar}"
        )
