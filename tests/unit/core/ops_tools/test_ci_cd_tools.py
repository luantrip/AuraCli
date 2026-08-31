"""Testes para CI/CD tools."""


class TestDeployment:
    """Testes para deployment."""

    def test_deployment_import(self):
        """Testa importação do módulo deployment."""
        from aura_cli.core.ops_tools.ci_cd import deployment

        assert deployment is not None


class TestGitHubActions:
    """Testes para github_actions."""

    def test_github_actions_import(self):
        """Testa importação do módulo github_actions."""
        from aura_cli.core.ops_tools.ci_cd import github_actions

        assert github_actions is not None


class TestPipelineManager:
    """Testes para pipeline_manager."""

    def test_pipeline_manager_import(self):
        """Testa importação do módulo pipeline_manager."""
        from aura_cli.core.ops_tools.ci_cd import pipeline_manager

        assert pipeline_manager is not None


class TestWorkflowAutomation:
    """Testes para workflow_automation."""

    def test_workflow_automation_import(self):
        """Testa importação do módulo workflow_automation."""
        from aura_cli.core.ops_tools.ci_cd import workflow_automation

        assert workflow_automation is not None
