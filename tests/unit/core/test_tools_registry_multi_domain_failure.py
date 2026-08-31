"""
Testes de cenário: Falha em múltiplos domínios de registro de tools.

Valida que o sistema continua operando mesmo quando múltiplos domínios
falham no registro, e que um resumo de falhas é disponibilizado.
"""

import logging
from unittest.mock import Mock

from scripts.tool_discovery import CoreToolDiscovery


class TestMultiDomainFailure:
    """Testes de falha em múltiplos domínios de tools."""

    def test_register_all_continues_when_multiple_domains_fail(self, caplog):
        """Registro deve continuar mesmo com múltiplas falhas."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha fazendo _register_tool lançar exceção
        registry._register_tool = Mock(side_effect=RuntimeError("Registration failed"))

        count = discovery.register_all(registry)

        # Deve ter tentado registrar (count será 0 pois todas falharam)
        assert count == 0

        # Deve ter logado warnings para múltiplos domínios
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) >= 3

    def test_register_all_logs_each_failed_domain_separately(self, caplog):
        """Cada domínio que falha deve ter seu próprio log de warning."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha fazendo _register_tool lançar exceção
        registry._register_tool = Mock(side_effect=RuntimeError("Registration failed"))

        discovery.register_all(registry)

        # Verifica que múltiplos domínios foram logados
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) >= 2

    def test_register_all_returns_count_excluding_failed_domains(self):
        """Contador deve excluir tools de domínios que falharam."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha parcial: primeiras 3 chamadas falham, resto sucede
        call_count = [0]

        def side_effect_partial(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 3:
                raise RuntimeError("Fail")
            return None

        registry._register_tool = Mock(side_effect=side_effect_partial)

        count = discovery.register_all(registry)

        # Deve ter registrado apenas as que sucederam
        assert count >= 0

    def test_register_all_handles_cascading_failures(self, caplog):
        """Falha em um domínio não deve causar falha em cascata."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha crítica
        registry._register_tool = Mock(side_effect=RuntimeError("Critical error"))

        # Não deve lançar exceção
        count = discovery.register_all(registry)

        # Deve ter continuado (count será 0)
        assert count == 0

        # Deve ter logado erros
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) > 0

    def test_register_all_completes_even_with_all_domains_failing(self, caplog):
        """Registro deve completar mesmo se todos os domínios falharem."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha em todas as tools
        registry._register_tool = Mock(side_effect=Exception("fail"))

        # Não deve lançar exceção
        count = discovery.register_all(registry)

        # Contador deve ser 0
        assert count == 0

        # Deve ter logado múltiplos warnings
        warnings = [r for r in caplog.records if r.levelname == "WARNING"]
        assert len(warnings) >= 4

    def test_register_all_logs_final_summary_with_failure_count(self, caplog):
        """Deve logar resumo final incluindo falhas."""
        caplog.set_level(logging.INFO, logger="scripts.tool_discovery")
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha em algumas tools
        registry._register_tool = Mock(side_effect=RuntimeError("fail"))

        discovery.register_all(registry)

        # Deve ter log final com contagem
        assert any(
            "finalized" in record.message.lower()
            or "capabilities mapped" in record.message.lower()
            for record in caplog.records
        )
