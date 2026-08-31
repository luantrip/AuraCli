"""
Testes unitários para os componentes de intervenção humana.

Garante que o refinamento visual minimalista não quebrou:
- render() retorna Panel com conteúdo esperado
- prompt_user() retorna dicionário com chaves approved, cancelled, reason, value
- Comportamento de confirmação (Sim/Não/Cancelar).

Nota: HumanInputDialog, HumanOptionSelector e HumanManualStepDisplay foram
removidos do codebase (código morto — zero uso em produção). Apenas
HumanConfirmationDialog e HumanDoubleConfirmationDialog são mantidos.
"""

from io import StringIO
from unittest.mock import patch

from rich.console import Console

from aura_cli.core.events.human_intervention_events import (
    InterventionContext,
    InterventionRequest,
    InterventionRequestType,
    RiskLevel,
)


def _make_confirm_request(
    prompt: str = "Confirma execução?",
    tool_name: str = "run_shell_command",
    tool_args: dict | None = None,
    risk_level: RiskLevel = RiskLevel.MEDIUM,
    timeout: int = 60,
) -> InterventionRequest:
    return InterventionRequest(
        task_id="test-task",
        request_id="req-1",
        request_type=InterventionRequestType.CONFIRM,
        prompt=prompt,
        context=InterventionContext(
            tool_name=tool_name,
            tool_args=tool_args or {"command": "echo ok"},
            risk_level=risk_level,
        ),
        timeout=timeout,
    )


def _panel_text(panel) -> str:
    """Render Panel to string for content assertions."""
    buf = StringIO()
    Console(file=buf, force_terminal=False).print(panel)
    return buf.getvalue()


class TestHumanConfirmationDialog:
    """Testes para HumanConfirmationDialog (visual minimalista)."""

    def test_render_returns_panel(self):
        from rich.panel import Panel

        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanConfirmationDialog,
        )

        dialog = HumanConfirmationDialog()
        request = _make_confirm_request()
        panel = dialog.render(request, show_timer=False)
        assert panel is not None
        assert isinstance(panel, Panel)
        content = _panel_text(panel)
        assert "Sim" in content or "Não" in content or "Cancelar" in content

    def test_render_includes_tool_context(self):
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanConfirmationDialog,
        )

        dialog = HumanConfirmationDialog()
        request = _make_confirm_request(
            tool_name="run_shell_command", tool_args={"command": "ls"}
        )
        panel = dialog.render(request, show_timer=False)
        content = _panel_text(panel)
        assert "run_shell_command" in content

    def test_render_risk_levels(self):
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanConfirmationDialog,
        )

        dialog = HumanConfirmationDialog()
        for level in (
            RiskLevel.LOW,
            RiskLevel.MEDIUM,
            RiskLevel.HIGH,
            RiskLevel.CRITICAL,
        ):
            request = _make_confirm_request()
            request.context.risk_level = level
            panel = dialog.render(request, show_timer=False)
            assert panel is not None

    @patch("rich.prompt.Prompt.ask")
    def test_prompt_user_approve_returns_approved_true(self, mock_ask):
        mock_ask.return_value = "y"
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanConfirmationDialog,
        )

        dialog = HumanConfirmationDialog()
        request = _make_confirm_request()
        result = dialog.prompt_user(request)
        assert result["approved"] is True
        assert result.get("value") == "Sim"

    @patch("rich.prompt.Prompt.ask")
    def test_prompt_user_deny_returns_approved_false(self, mock_ask):
        mock_ask.return_value = "n"
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanConfirmationDialog,
        )

        dialog = HumanConfirmationDialog()
        request = _make_confirm_request()
        result = dialog.prompt_user(request)
        assert result["approved"] is False
        assert result.get("value") == "Não"

    @patch("rich.prompt.Prompt.ask")
    def test_prompt_user_cancel_returns_cancelled(self, mock_ask):
        mock_ask.return_value = "c"
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanConfirmationDialog,
        )

        dialog = HumanConfirmationDialog()
        request = _make_confirm_request()
        result = dialog.prompt_user(request)
        assert result.get("approved") is False
        assert result.get("cancelled") is True
        assert result.get("reason") == "user_cancelled"

    @patch("rich.prompt.Prompt.ask")
    def test_prompt_user_sim_pt_approved(self, mock_ask):
        mock_ask.return_value = "s"
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanConfirmationDialog,
        )

        dialog = HumanConfirmationDialog()
        request = _make_confirm_request()
        result = dialog.prompt_user(request)
        assert result["approved"] is True


class TestHumanDoubleConfirmationDialog:
    """Testes para confirmação dupla (Safety Lock)."""

    @patch("rich.prompt.Prompt.ask")
    def test_double_confirm_deny_first_returns_deny(self, mock_ask):
        mock_ask.return_value = "n"
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanDoubleConfirmationDialog,
        )

        dialog = HumanDoubleConfirmationDialog()
        request = _make_confirm_request()
        result = dialog.prompt_user(request)
        assert result["approved"] is False
        assert mock_ask.call_count == 1

    @patch("rich.prompt.Prompt.ask")
    def test_double_confirm_approve_twice_returns_approved(self, mock_ask):
        mock_ask.side_effect = ["y", "y"]
        from aura_cli.cli.ui.components.human_confirmation_dialog import (
            HumanDoubleConfirmationDialog,
        )

        dialog = HumanDoubleConfirmationDialog()
        request = _make_confirm_request()
        result = dialog.prompt_user(request)
        assert result["approved"] is True
        assert mock_ask.call_count >= 2
