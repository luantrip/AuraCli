"""
Testes de cenário: Falha em domínio crítico de registro de tools.

Valida que falhas em domínios críticos (file_system, shell) são tratadas
com severidade apropriada e afetam disponibilidade de funcionalidades.
"""

from unittest.mock import Mock

from scripts.tool_discovery import CoreToolDiscovery


class TestCriticalDomainFailure:
    """Testes de falha em domínios críticos de tools."""

    def test_register_file_system_tools_failure_is_logged_with_warning(self, caplog):
        """Falha em domínio crítico (file_system) deve ser logada como warning."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha fazendo _register_tool lançar exceção
        registry._register_tool = Mock(side_effect=RuntimeError("Registration failed"))

        discovery._register_file_system_tools(registry)

        # Verifica que warning foi logado
        assert any(
            "Erro ao registrar file_system tools" in record.message
            for record in caplog.records
        )
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_register_shell_tools_failure_is_logged_with_warning(self, caplog):
        """Falha em domínio crítico (shell) deve ser logada como warning."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha fazendo _register_tool lançar exceção
        registry._register_tool = Mock(side_effect=RuntimeError("Registration failed"))

        discovery._register_shell_tools(registry)

        # Verifica que warning foi logado
        assert any(
            "Erro ao registrar shell tools" in record.message
            for record in caplog.records
        )
        assert any(record.levelname == "WARNING" for record in caplog.records)

    def test_register_file_system_tools_failure_does_not_increment_counter(self):
        """Falha em file_system não deve incrementar contador de tools registradas."""
        discovery = CoreToolDiscovery()
        registry = Mock()
        initial_count = discovery.tools_registered

        # Simula falha fazendo _register_tool lançar exceção
        registry._register_tool = Mock(side_effect=RuntimeError("Registration failed"))

        discovery._register_file_system_tools(registry)

        # Contador não deve ter mudado
        assert discovery.tools_registered == initial_count

    def test_register_shell_tools_failure_does_not_increment_counter(self):
        """Falha em shell não deve incrementar contador de tools registradas."""
        discovery = CoreToolDiscovery()
        registry = Mock()
        initial_count = discovery.tools_registered

        # Simula falha fazendo _register_tool lançar exceção
        registry._register_tool = Mock(side_effect=RuntimeError("Registration failed"))

        discovery._register_shell_tools(registry)

        # Contador não deve ter mudado
        assert discovery.tools_registered == initial_count

    def test_register_git_tools_failure_is_logged_with_warning(self, caplog):
        """Falha em domínio git deve ser logada como warning."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha fazendo _register_tool lançar exceção
        registry._register_tool = Mock(side_effect=RuntimeError("Registration failed"))

        discovery._register_git_tools(registry)

        # Verifica que warning foi logado
        assert any(
            "Erro ao registrar git tools" in record.message for record in caplog.records
        )

    def test_register_docker_tools_failure_is_logged_with_warning(self, caplog):
        """Falha em domínio docker deve ser logada como warning."""
        discovery = CoreToolDiscovery()
        registry = Mock()

        # Simula falha fazendo _register_tool lançar exceção
        registry._register_tool = Mock(side_effect=RuntimeError("Registration failed"))

        discovery._register_docker_tools(registry)

        # Verifica que warning foi logado
        assert any(
            "Erro ao registrar docker tools" in record.message
            for record in caplog.records
        )
