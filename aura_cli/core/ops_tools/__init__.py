"""DevOps tools package for the Ops agent.

Re-exports tools across: Git, Docker, Monitoring, CI/CD, Security,
Infrastructure (Kubernetes, Terraform, cloud providers), and Database.
All tools are registered for function-calling by the Ops agent.
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
from aura_cli.core.ops_tools.ci_cd.pipeline_manager import Pipeline, PipelineManager
from aura_cli.core.ops_tools.ci_cd.workflow_automation import (
    WorkflowAutomator,
    automate_workflow,
)
from aura_cli.core.ops_tools.database.database_backup import (
    BackupConfig,
    DatabaseBackup,
    DatabaseType,
)
from aura_cli.core.ops_tools.database.database_migration import (
    DatabaseMigration,
    MigrationStatus,
)
from aura_cli.core.ops_tools.database.database_monitor import DatabaseMonitor
from aura_cli.core.ops_tools.database.query_executor import (
    DatabaseConnection,
    QueryExecutor,
    QueryResult,
)
from aura_cli.core.ops_tools.docker import (
    docker_build,
    docker_compose,
    docker_exec,
    docker_images,
    docker_logs,
    docker_ps,
)
from aura_cli.core.ops_tools.git import (
    git_branch,
    git_commit,
    git_commit_smart,
    git_diff,
    git_log,
    git_smart,
    git_status,
)
from aura_cli.core.ops_tools.infrastructure.cloud_providers import (
    AWSManager,
    AzureManager,
    GCPManager,
)
from aura_cli.core.ops_tools.infrastructure.infrastructure_as_code import IaCManager
from aura_cli.core.ops_tools.infrastructure.kubernetes import KubernetesManager
from aura_cli.core.ops_tools.infrastructure.terraform import (
    TerraformManager,
    TerraformPlan,
)
from aura_cli.core.ops_tools.monitoring.alerting_system import (
    AlertingSystem,
    AlertSeverity,
)
from aura_cli.core.ops_tools.monitoring.dashboard import MonitoringDashboard
from aura_cli.core.ops_tools.monitoring.health import (
    check_port,
    check_service_health,
    process_info,
    system_resources,
)
from aura_cli.core.ops_tools.monitoring.logs_aggregator import LogLevel, LogsAggregator
from aura_cli.core.ops_tools.monitoring.metrics_collector import (
    MetricsCollector,
    MetricType,
)
from aura_cli.core.ops_tools.monitoring.performance_monitor import PerformanceMonitor
from aura_cli.core.ops_tools.security.access_control import AccessControl, Permission
from aura_cli.core.ops_tools.security.secret_manager import SecretManager, SecretType
from aura_cli.core.ops_tools.security.security_audit import SecurityAuditor
from aura_cli.core.ops_tools.security.vulnerability_scanner import (
    Severity,
    VulnerabilityScanner,
)

__all__ = [
    "AWSManager",
    "AccessControl",
    "AlertSeverity",
    "AlertingSystem",
    "AzureManager",
    "BackupConfig",
    "DatabaseBackup",
    "DatabaseConnection",
    "DatabaseMigration",
    "DatabaseMonitor",
    "DatabaseType",
    "DeploymentConfig",
    "GCPManager",
    "IaCManager",
    "KubernetesManager",
    "LogLevel",
    "LogsAggregator",
    "MetricType",
    "MetricsCollector",
    "MigrationStatus",
    "MonitoringDashboard",
    "PerformanceMonitor",
    "Permission",
    "Pipeline",
    "PipelineManager",
    "QueryExecutor",
    "QueryResult",
    "SecretManager",
    "SecretType",
    "SecurityAuditor",
    "Severity",
    "TerraformManager",
    "TerraformPlan",
    "VulnerabilityScanner",
    "WorkflowAutomator",
    "WorkflowConfig",
    "automate_workflow",
    "check_port",
    "check_service_health",
    "create_workflow",
    "deploy_application",
    "docker_build",
    "docker_compose",
    "docker_exec",
    "docker_images",
    "docker_logs",
    "docker_ps",
    "get_deployment_status",
    "get_workflow_status",
    "git_branch",
    "git_commit",
    "git_commit_smart",
    "git_diff",
    "git_log",
    "git_smart",
    "git_status",
    "list_workflows",
    "process_info",
    "rollback_deployment",
    "run_workflow",
    "system_resources",
]
