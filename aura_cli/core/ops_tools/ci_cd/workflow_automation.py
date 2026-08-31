"""
Workflow automation for Aura CLI.

Provides automated creation and management of CI/CD workflows
with templates and pre-defined configurations.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


@dataclass
class WorkflowTemplate:
    """Workflow template (name, description, triggers, steps)."""

    name: str
    description: str
    triggers: List[str]
    steps: List[Dict[str, Any]]
    variables: Dict[str, Any] = field(default_factory=dict)


class WorkflowAutomator:
    """Workflow automator from templates."""

    def __init__(self):
        """Initialise the workflow automator."""
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.stats = get_stats()

        self._load_default_templates()

        logger.info(f"WorkflowAutomator initialized ({len(self.templates)} templates)")

    def _load_default_templates(self) -> None:
        """Load the built-in default templates."""
        ci_template = WorkflowTemplate(
            name="ci_basic",
            description="CI básico com testes",
            triggers=["push", "pull_request"],
            steps=[
                {"name": "Checkout", "uses": "actions/checkout@v3"},
                {
                    "name": "Setup Python",
                    "uses": "actions/setup-python@v4",
                    "with": {"python-version": "3.10"},
                },
                {
                    "name": "Install dependencies",
                    "run": "pip install -r requirements.txt",
                },
                {"name": "Run tests", "run": "pytest"},
            ],
        )
        self.templates["ci_basic"] = ci_template

        deploy_template = WorkflowTemplate(
            name="deploy",
            description="Deploy automático",
            triggers=["push"],
            steps=[
                {"name": "Checkout", "uses": "actions/checkout@v3"},
                {"name": "Deploy", "run": "echo 'Deploy steps here'"},
            ],
            variables={"environment": "production"},
        )
        self.templates["deploy"] = deploy_template

        logger.debug(f"Default templates loaded: {list(self.templates.keys())}")

    def register_template(self, template: WorkflowTemplate) -> None:
        """Register a workflow template."""
        self.templates[template.name] = template
        logger.info(f"Template '{template.name}' registrado")

    def create_from_template(
        self,
        template_name: str,
        workflow_name: str,
        customizations: Optional[Dict[str, Any]] = None,
        output_path: str = ".github/workflows",
    ) -> str:
        """Create a workflow from a template."""
        from aura_cli.core.ops_tools.ci_cd.github_actions import (
            WorkflowConfig,
            create_workflow,
        )
        from aura_cli.core.ui import display_tool_call

        display_tool_call(
            "create_from_template",
            {"template_name": template_name, "workflow_name": workflow_name},
        )

        if template_name not in self.templates:
            error_msg = f"Template '{template_name}' not found"
            logger.error(error_msg)
            return error_msg

        template = self.templates[template_name]
        customizations = customizations or {}

        triggers = customizations.get("triggers", template.triggers)
        steps = customizations.get("steps", template.steps)
        variables = {**template.variables, **customizations.get("variables", {})}

        config = WorkflowConfig(
            name=workflow_name,
            on={trigger: {} for trigger in triggers},
            jobs={"build": {"runs-on": "ubuntu-latest", "steps": steps}},
            env=variables,
        )

        result = create_workflow(workflow_name, config, output_path)

        self.stats.track_tool_usage("workflow_automation")

        return result

    def list_templates(self) -> List[Dict[str, Any]]:
        """Return a list of available templates."""
        return [
            {"name": t.name, "description": t.description, "triggers": t.triggers}
            for t in self.templates.values()
        ]


def automate_workflow(
    template_name: str,
    workflow_name: str,
    customizations: Optional[Dict[str, Any]] = None,
) -> str:
    """Automate a workflow task end-to-end."""
    automator = WorkflowAutomator()
    return automator.create_from_template(template_name, workflow_name, customizations)
