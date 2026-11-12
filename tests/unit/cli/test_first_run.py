"""Tests for the first-run onboarding wizard (P0-4, P1-4).

P0-4: skipping onboarding must persist a marker so the wizard is not shown on
every launch. P1-4: keys entered during setup must be validated (non-blocking).
"""

from unittest.mock import MagicMock, patch

import pytest


class TestIsFirstRun:
    def test_no_config_file_is_first_run(self):
        from aura_cli.cli import first_run

        fake_path = MagicMock()
        fake_path.exists.return_value = False
        with patch.object(first_run, "CONFIG_FILE", fake_path):
            assert first_run.is_first_run() is True

    def test_config_exists_but_marker_set_is_not_first_run(self):
        from aura_cli.cli import first_run

        fake_path = MagicMock()
        fake_path.exists.return_value = True
        fake_config = MagicMock()
        fake_config.get.return_value = True  # onboarding_completed
        with patch.object(first_run, "CONFIG_FILE", fake_path):
            with patch(
                "aura_cli.core.config.get_config_manager", return_value=fake_config
            ):
                assert first_run.is_first_run() is False

    def test_config_exists_without_marker_is_first_run(self):
        from aura_cli.cli import first_run

        fake_path = MagicMock()
        fake_path.exists.return_value = True
        fake_config = MagicMock()
        fake_config.get.return_value = None  # marker never set
        with patch.object(first_run, "CONFIG_FILE", fake_path):
            with patch(
                "aura_cli.core.config.get_config_manager", return_value=fake_config
            ):
                assert first_run.is_first_run() is True


class TestSkipPersistsMarker:
    def test_skip_marks_onboarding_complete(self):
        from aura_cli.cli import first_run

        fake_config = MagicMock()
        with (
            patch("aura_cli.core.config.get_config_manager", return_value=fake_config),
            patch("aura_cli.cli.ui.prompts.select_dialog") as mock_select,
        ):
            mock_select.return_value.run.return_value = first_run._MODE_SKIP
            result = first_run.run_setup_wizard()

        assert result is False
        # Marker must be persisted so the wizard is not shown again.
        fake_config.set.assert_any_call("onboarding_completed", True)
        fake_config.save.assert_called()

    def test_cancel_with_escape_is_treated_as_skip(self):
        from aura_cli.cli import first_run

        fake_config = MagicMock()
        with (
            patch("aura_cli.core.config.get_config_manager", return_value=fake_config),
            patch("aura_cli.cli.ui.prompts.select_dialog") as mock_select,
        ):
            mock_select.return_value.run.return_value = None  # Esc
            assert first_run.run_setup_wizard() is False

        fake_config.set.assert_any_call("onboarding_completed", True)


class TestWizardDrivenByRealKeys:
    """End-to-end through the real prompt layer with simulated key presses."""

    ENTER, ESC, DOWN = "\r", "\x1b", "\x1b[B"

    def _run(self, keys: str):
        import signal

        from prompt_toolkit.application import create_app_session
        from prompt_toolkit.input import create_pipe_input
        from prompt_toolkit.output import DummyOutput

        from aura_cli.cli import first_run

        class _Hung(BaseException):  # not an Exception: the wizard must not swallow it
            pass

        def _alarm(*_a):
            raise _Hung(f"wizard still waiting for input after {keys!r}")

        previous = signal.signal(signal.SIGALRM, _alarm)
        signal.alarm(8)
        try:
            with create_pipe_input() as pipe:
                pipe.send_text(keys)
                with create_app_session(input=pipe, output=DummyOutput()):
                    return first_run.run_setup_wizard()
        except _Hung as hung:
            pytest.fail(str(hung))
        finally:
            signal.alarm(0)
            signal.signal(signal.SIGALRM, previous)

    def test_enter_on_default_runs_multi_provider_and_all_skipped_returns_false(self):
        # Enter picks "4 gratuitos"; each of the 4 key prompts is skipped (empty line).
        with patch("aura_cli.cli.first_run._save_provider_key") as save:
            assert self._run(self.ENTER * 5) is False
        save.assert_not_called()

    def test_down_down_enter_is_skip_and_persists_marker(self):
        fake_config = MagicMock()
        with patch("aura_cli.core.config.get_config_manager", return_value=fake_config):
            assert self._run(self.DOWN * 2 + self.ENTER) is False
        fake_config.set.assert_any_call("onboarding_completed", True)

    def test_multi_provider_saves_typed_key_and_completes(self):
        fake_config = MagicMock()
        with (
            patch("aura_cli.core.config.get_config_manager", return_value=fake_config),
            patch("aura_cli.cli.first_run._save_provider_key") as save,
            patch(
                "aura_cli.cli.first_run._validate_key_nonblocking",
                return_value=(True, ""),
            ),
        ):
            # Enter -> multi; type a Google key; skip the other three (empty line).
            result = self._run(self.ENTER + "AIza-test" + self.ENTER * 4)

        assert result is True
        save.assert_called_once_with("google", "AIza-test")
        fake_config.set.assert_any_call("onboarding_completed", True)

    def test_single_provider_flow_saves_chosen_provider(self):
        fake_config = MagicMock()
        with (
            patch("aura_cli.core.config.get_config_manager", return_value=fake_config),
            patch("aura_cli.cli.first_run._save_provider_key") as save,
            patch(
                "aura_cli.cli.first_run._validate_key_nonblocking",
                return_value=(True, ""),
            ),
        ):
            # Down -> "1 provider"; Enter; Down -> Cerebras; Enter; type key; Enter.
            keys = (
                self.DOWN + self.ENTER + self.DOWN + self.ENTER + "csk-1" + self.ENTER
            )
            assert self._run(keys) is True

        save.assert_called_once_with("cerebras", "csk-1")


class TestKeyValidation:
    def test_validate_key_nonblocking_ok(self):
        from aura_cli.cli import first_run

        with patch(
            "aura_cli.core.llm.api_validator.quick_test_api_key",
            return_value=(True, "ok"),
        ):
            ok, _ = first_run._validate_key_nonblocking("google", "AIza-x")
        assert ok is True

    def test_validate_key_nonblocking_invalid(self):
        from aura_cli.cli import first_run

        with patch(
            "aura_cli.core.llm.api_validator.quick_test_api_key",
            return_value=(False, "invalid"),
        ):
            ok, detail = first_run._validate_key_nonblocking("google", "bad")
        assert ok is False
        assert "invalid" in detail

    def test_validate_key_swallows_exceptions(self):
        from aura_cli.cli import first_run

        with patch(
            "aura_cli.core.llm.api_validator.quick_test_api_key",
            side_effect=RuntimeError("boom"),
        ):
            ok, detail = first_run._validate_key_nonblocking("google", "x")
        assert ok is False
        assert "boom" in detail
