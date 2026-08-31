"""
Testes para o módulo workflow_automation.

Testa funcionalidades de automação de workflows CI/CD
com templates e configurações pré-definidas.
"""

from aura_cli.core.ops_tools.ci_cd.workflow_automation import (
    WorkflowAutomator,
    WorkflowTemplate,
)


class TestWorkflowTemplate:
    """Testa dataclass WorkflowTemplate."""

    def test_workflow_template_creation(self):
        """Testa criação de template de workflow."""
        triggers = ["push", "pull_request"]
        steps = [
            {"name": "Checkout", "uses": "actions/checkout@v3"},
            {"name": "Setup Node", "uses": "actions/setup-node@v3"},
        ]

        template = WorkflowTemplate(
            name="Node.js CI",
            description="CI pipeline for Node.js projects",
            triggers=triggers,
            steps=steps,
        )

        assert template.name == "Node.js CI"
        assert template.description == "CI pipeline for Node.js projects"
        assert template.triggers == triggers
        assert template.steps == steps
        assert template.variables == {}

    def test_workflow_template_with_variables(self):
        """Testa template com variáveis."""
        variables = {"node_version": "18", "cache_key": "node-modules"}

        template = WorkflowTemplate(
            name="Custom Template",
            description="Template with variables",
            triggers=["push"],
            steps=[{"name": "Test"}],
            variables=variables,
        )

        assert template.variables == variables


class TestWorkflowAutomator:
    """Testa classe WorkflowAutomator."""

    def setup_method(self):
        """Setup para cada teste."""
        self.automator = WorkflowAutomator()

    def test_init(self):
        """Testa inicialização."""
        assert hasattr(self.automator, "templates")
        assert isinstance(self.automator.templates, dict)
