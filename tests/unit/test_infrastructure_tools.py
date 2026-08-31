"""Testes para infrastructure tools."""


class TestCloudProviders:
    """Testes para cloud_providers."""

    def test_cloud_providers_import(self):
        """Testa importação do módulo cloud_providers."""
        from aura_cli.core.ops_tools.infrastructure import cloud_providers

        assert cloud_providers is not None


class TestInfrastructureAsCode:
    """Testes para infrastructure_as_code."""

    def test_infrastructure_as_code_import(self):
        """Testa importação do módulo infrastructure_as_code."""
        from aura_cli.core.ops_tools.infrastructure import infrastructure_as_code

        assert infrastructure_as_code is not None


class TestKubernetes:
    """Testes para kubernetes."""

    def test_kubernetes_import(self):
        """Testa importação do módulo kubernetes."""
        from aura_cli.core.ops_tools.infrastructure import kubernetes

        assert kubernetes is not None


class TestTerraform:
    """Testes para terraform."""

    def test_terraform_import(self):
        """Testa importação do módulo terraform."""
        from aura_cli.core.ops_tools.infrastructure import terraform

        assert terraform is not None
