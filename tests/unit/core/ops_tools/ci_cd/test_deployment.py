"""
Testes para o módulo deployment.

Testa funcionalidades de deployment, rollback
e monitoramento de deployments.
"""

from aura_cli.core.ops_tools.ci_cd.deployment import (
    DeploymentConfig,
    DeploymentStatus,
)


class TestDeploymentStatus:
    """Testa enum DeploymentStatus."""

    def test_deployment_status_values(self):
        """Testa valores de status de deployment."""
        assert DeploymentStatus.PENDING.value == "pending"
        assert DeploymentStatus.IN_PROGRESS.value == "in_progress"
        assert DeploymentStatus.SUCCESS.value == "success"
        assert DeploymentStatus.FAILED.value == "failed"
        assert DeploymentStatus.ROLLED_BACK.value == "rolled_back"


class TestDeploymentConfig:
    """Testa dataclass DeploymentConfig."""

    def test_deployment_config_creation(self):
        """Testa criação de configuração de deployment."""
        config = DeploymentConfig(environment="production", version="v1.2.3")

        assert config.environment == "production"
        assert config.version == "v1.2.3"
        assert config.strategy == "rolling"  # Default
        assert config.rollback_on_error is True  # Default
        assert config.health_check_url is None

    def test_deployment_config_custom(self):
        """Testa configuração customizada."""
        config = DeploymentConfig(
            environment="staging",
            version="v2.0.0-beta",
            strategy="blue-green",
            rollback_on_error=False,
            health_check_url="https://api.example.com/health",
        )

        assert config.strategy == "blue-green"
        assert config.rollback_on_error is False
        assert config.health_check_url == "https://api.example.com/health"

    def test_deployment_strategies(self):
        """Testa diferentes estratégias de deployment."""
        strategies = ["rolling", "blue-green", "canary", "recreate"]

        for strategy in strategies:
            config = DeploymentConfig(
                environment="test", version="v1.0.0", strategy=strategy
            )
            assert config.strategy == strategy
