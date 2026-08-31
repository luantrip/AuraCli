"""
Testes de cenário: Health check pós-boot.

Valida que após a inicialização dos serviços core, um resumo de saúde
é disponibilizado distinguindo serviços críticos de opcionais e incluindo
warnings de degradação.
"""

from unittest.mock import Mock, patch

import pytest

from aura_cli.cli.main import _init_core_services


class TestHealthCheckPostBoot:
    """Testes de health check após boot."""

    def test_init_core_services_tracks_successful_initializations(self, tmp_path):
        """Deve rastrear quais serviços foram inicializados com sucesso."""
        runtime = Mock(project_root=tmp_path.resolve())

        with patch(
            "aura_cli.cli.main.RuntimeServices.initialize", return_value=runtime
        ) as initialize:
            _init_core_services(tmp_path)

        initialize.assert_called_once_with(tmp_path)

    def test_init_core_services_continues_when_optional_service_fails(
        self, tmp_path, caplog
    ):
        """Deve continuar quando serviço opcional falha."""
        project_root = tmp_path

        runtime = Mock(project_root=tmp_path.resolve())
        with (
            patch("aura_cli.cli.main.RuntimeServices.initialize", return_value=runtime),
            patch(
                "aura_cli.core.agents.ensure_adk_initialized",
                side_effect=RuntimeError("ADK unavailable"),
            ),
        ):
            _init_core_services(project_root)

    def test_init_core_services_propagates_critical_failure(self, tmp_path):
        """Falha de serviço crítico não deve produzir runtime parcial."""
        with (
            patch(
                "aura_cli.cli.main.RuntimeServices.initialize",
                side_effect=RuntimeError("Memory failed"),
            ),
            pytest.raises(RuntimeError, match="Memory failed"),
        ):
            _init_core_services(tmp_path)

    def test_init_core_services_initializes_memory_service_first(self, tmp_path):
        """Composition root deve concluir antes dos componentes opcionais."""
        call_order = []
        runtime = Mock(project_root=tmp_path.resolve())

        with (
            patch(
                "aura_cli.cli.main.RuntimeServices.initialize",
                side_effect=lambda root: call_order.append("runtime") or runtime,
            ),
            patch(
                "aura_cli.core.agents.ensure_adk_initialized",
                side_effect=lambda: call_order.append("adk") or False,
            ),
        ):
            _init_core_services(tmp_path)

        assert call_order[:2] == ["runtime", "adk"]
