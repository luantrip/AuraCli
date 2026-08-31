"""
CI/CD tools for Aura CLI.

Provides functionality for:
- GitHub Actions integration
- Workflow automation
- Deployment tools
- Pipeline management
"""

from aura_cli.core.ops_tools.ci_cd.deployment import (
    DeploymentConfig,
    deploy_application,
    get_deployment_status,
    rollback_deployment,
)
from aura_cli.core.ops_tools.ci_cd.github_actions import (
    WorkflowConfig,
    create_workflow,
    get_workflow_status,
    list_workflows,
    run_workflow,
)
from aura_cli.core.ops_tools.ci_cd.pipeline_manager import (
    Pipeline,
    PipelineManager,
    PipelineStage,
)
from aura_cli.core.ops_tools.ci_cd.workflow_automation import (
    WorkflowAutomator,
    WorkflowTemplate,
    automate_workflow,
)

__all__ = [
    "DeploymentConfig",
    "Pipeline",
    "PipelineManager",
    "PipelineStage",
    "WorkflowAutomator",
    "WorkflowConfig",
    "WorkflowTemplate",
    "automate_workflow",
    "create_workflow",
    "deploy_application",
    "get_deployment_status",
    "get_workflow_status",
    "list_workflows",
    "rollback_deployment",
    "run_workflow",
]
