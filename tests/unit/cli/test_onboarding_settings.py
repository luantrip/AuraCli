"""P2-2, P2-3, P2-5, P2-6, P2-7 — onboarding / settings polish.

Acceptance tests for the five items closed in this batch:
  P2-2  Provider count is dynamic (len(PROVIDER_SPECS)), not a hard-coded literal.
  P2-3  Saving a model without the provider key emits a warning.
  P2-5  After entering a key, a masked preview is shown (prefix + char count).
  P2-6  The onboarding hint is suppressed when the setup wizard just ran.
  P2-7  The fallback settings prompt bound says "(1-10)", matching its 10 options.
"""

from __future__ import annotations

from io import StringIO
import re
from unittest.mock import MagicMock, patch

# ─────────────────────────────────────────────────────────────────────────────
# --- Dynamic provider count ---
# ─────────────────────────────────────────────────────────────────────────────


class TestDynamicProviderCount:
    def test_settings_summary_total_matches_provider_specs(self) -> None:
        """The '/N providers' total must equal len(PROVIDER_SPECS), not 6 or 7."""
        from aura_cli.cli.ui.settings_modal import settings_summary
        from aura_cli.core.llm.provider_spec import PROVIDER_SPECS

        expected_total = len(PROVIDER_SPECS)
        summary = settings_summary(2, "Gemini Flash", "dark")
        assert f"2/{expected_total} providers" in summary, (
            f"Expected '2/{expected_total} providers'; got: {summary!r}"
        )

    def test_settings_summary_total_grows_with_provider_specs(
        self, monkeypatch
    ) -> None:
        """Adding a provider spec must raise the denominator without touching the UI."""
        from aura_cli.core.llm import provider_spec as ps

        extra_spec = ps.ProviderSpec(
            "testprov", "testprov", "TestProv", ("TESTPROV_API_KEY",)
        )
        extended = (*ps.PROVIDER_SPECS, extra_spec)
        monkeypatch.setattr(ps, "PROVIDER_SPECS", extended)

        from aura_cli.cli.ui.settings_modal import settings_summary

        summary = settings_summary(1, "Model", "dark")
        expected_total = len(extended)
        assert f"1/{expected_total} providers" in summary

    def test_settings_summary_navigation_hint_is_english(self) -> None:
        from aura_cli.cli.ui.settings_modal import settings_summary

        summary = settings_summary(0, "none", "light")
        assert "Esc back" in summary
        # must NOT contain the old Portuguese navigation hint
        assert "Esc voltar" not in summary


# ─────────────────────────────────────────────────────────────────────────────
# --- Model save without provider key ---
# ─────────────────────────────────────────────────────────────────────────────


class TestModelSaveWithoutKey:
    def _run_handle_model(
        self,
        chosen_model: str,
        api_keys: dict,
        buf: StringIO,
    ) -> str:
        """Run handle_model() with faked dialog and API key dict."""
        from aura_cli.cli.commands import config as cfg_mod
        from aura_cli.core.llm.model_utils import get_valid_models

        models = get_valid_models()
        app = MagicMock()
        app.run.return_value = chosen_model

        from rich.console import Console

        fake_console = Console(file=buf, color_system=None)

        with (
            patch.object(cfg_mod, "get_valid_models", return_value=models),
            patch("aura_cli.cli.helpers.get_api_keys_dict", return_value=api_keys),
            patch("aura_cli.cli.ui.prompts.select_dialog", return_value=app),
            patch("aura_cli.cli.commands.config.config_manager") as mock_cfg,
            patch(
                "aura_cli.cli.commands.config.get_console", return_value=fake_console
            ),
        ):
            mock_cfg.get.return_value = ""
            from aura_cli.cli.commands.config import handle_model

            return handle_model("")

    def test_no_warning_when_provider_key_is_configured(self) -> None:
        """No warning when the selected model's provider has a key."""
        buf = StringIO()
        result = self._run_handle_model(
            "gemini/gemini-2.5-flash",
            api_keys={"GOOGLE_API_KEY": "AIzaFAKEKEY"},
            buf=buf,
        )
        assert result == "gemini/gemini-2.5-flash"
        assert "API key" not in buf.getvalue()

    def test_warning_when_provider_key_is_missing(self) -> None:
        """Warning is emitted when the provider has no configured key."""
        buf = StringIO()
        self._run_handle_model(
            "gemini/gemini-2.5-flash",
            api_keys={},  # no keys at all
            buf=buf,
        )
        output = buf.getvalue()
        assert "API key" in output or "provider" in output.lower()


# ─────────────────────────────────────────────────────────────────────────────
# --- Masked API key preview ---
# ─────────────────────────────────────────────────────────────────────────────


class TestMaskedKeyPreview:
    def _preview(self, key: str) -> str:
        from aura_cli.cli.first_run import _masked_key_preview

        return _masked_key_preview(key)

    def test_shows_prefix_not_full_key(self) -> None:
        key = "AIzaSyABCDEFGHIJKLMNOPQRSTUVWXYZ123456"
        preview = self._preview(key)
        assert key not in preview, "full key must not appear in preview"
        assert "AIzaSyAB" in preview, "first 8 chars should be visible"

    def test_includes_char_count(self) -> None:
        key = "sk-abcdefghijklmnop"
        preview = self._preview(key)
        assert str(len(key)) in preview

    def test_masked_middle_present(self) -> None:
        preview = self._preview("ABCDEFGHIJ")
        # some masking characters should be present
        assert "·" in preview or "*" in preview or len(preview) < len("ABCDEFGHIJ")

    def test_empty_key_returns_marker(self) -> None:
        assert self._preview("") == "(empty)"

    def test_short_key_does_not_crash(self) -> None:
        preview = self._preview("AB")
        assert "2" in preview  # char count appears


# ─────────────────────────────────────────────────────────────────────────────
# --- Onboarding hint suppression ---
# ─────────────────────────────────────────────────────────────────────────────


class TestOnboardingHintSuppression:
    def _hint_called(self, wizard_ran: bool, monkeypatch) -> bool:
        """Return True if show_onboarding_hint_if_first_run would be called."""
        from aura_cli.cli.main import _maybe_show_onboarding_hint

        called: list[bool] = []
        monkeypatch.setattr(
            "aura_cli.cli.main.show_onboarding_hint_if_first_run",
            lambda **_kw: called.append(True),
        )
        _maybe_show_onboarding_hint(ui=MagicMock(), wizard_ran=wizard_ran)
        return bool(called)

    def test_hint_suppressed_when_wizard_ran(self, monkeypatch) -> None:
        assert not self._hint_called(wizard_ran=True, monkeypatch=monkeypatch)

    def test_hint_shown_on_normal_session(self, monkeypatch) -> None:
        assert self._hint_called(wizard_ran=False, monkeypatch=monkeypatch)


# ─────────────────────────────────────────────────────────────────────────────
# --- Fallback prompt bound ---
# ─────────────────────────────────────────────────────────────────────────────


class TestFallbackPromptBound:
    def test_fallback_prompt_bound_matches_option_count(self) -> None:
        """The '(1-N)' bound in the fallback prompt must include all listed options."""
        from pathlib import Path

        source = Path("aura_cli/cli/key_manager.py").read_text(encoding="utf-8")

        # Isolate the _show_settings_fallback function body
        fn_start = source.index("def _show_settings_fallback(")
        fn_body = source[fn_start : fn_start + 5000]

        # Find the bound string: "(1-N)" near "Choose an option"
        match = re.search(r"Choose an option \(1-(\d+)\)", fn_body)
        assert match, "fallback prompt must contain 'Choose an option (1-N)'"
        bound = int(match.group(1))

        # Count explicit option rows: table.add_row("N", ...) with numeric first arg
        rows = re.findall(r'table\.add_row\(\s*["\'](\d+)["\']', fn_body)
        assert rows, "fallback table must have numbered rows"
        max_row = max(int(r) for r in rows)
        assert bound == max_row, (
            f"fallback prompt says '(1-{bound})' but highest row is {max_row}"
        )
