"""OPS Tools Map — available tools for the Ops agent.

Defines OPS_TOOLS (dict name→callable), OPS_TOOL_CATEGORIES and
get_ops_tools_for_mode() to filter tools by operation mode
(git, docker, k8s, etc).rraform, security, db, cicd, general).

Anteriormente nomeado cli/constants.py — renomeado pto reflect
the real content (not a constants file constantes CLI).
"""

from aura_cli.core.logger import get_logger

# --- Git tools (canonical: core/ops_tools/git/) ---
# --- Deployment ---
from aura_cli.core.ops_tools.ci_cd.deployment import (
    check_deployment_health as deploy_check_deployment_health,
)
from aura_cli.core.ops_tools.ci_cd.deployment import (
    deploy_application as deploy_deploy_application,
)
from aura_cli.core.ops_tools.ci_cd.deployment import (
    get_deployment_status as deploy_get_deployment_status,
)
from aura_cli.core.ops_tools.ci_cd.deployment import (
    rollback_deployment as deploy_rollback_deployment,
)

# --- CI/CD: GitHub Actions ---
from aura_cli.core.ops_tools.ci_cd.github_actions import (
    create_workflow as gh_create_workflow,
)
from aura_cli.core.ops_tools.ci_cd.github_actions import (
    get_workflow_status as gh_get_workflow_status,
)
from aura_cli.core.ops_tools.ci_cd.github_actions import (
    list_workflows as gh_list_workflows,
)
from aura_cli.core.ops_tools.ci_cd.github_actions import (
    run_workflow as gh_run_workflow,
)

# --- Docker tools (canonical: core/ops_tools/docker/) ---
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
    git_diff_context,
    git_log,
    git_smart,
    git_status,
)

# --- System / Network tools (canonical: core/tools/ops_tools.py) ---
from aura_cli.core.ops_tools.monitoring.health import (
    check_port,
    check_service_health,
    process_info,
    system_resources,
)

# --- Cloud tools ---
from aura_cli.core.tools.cloud_ops import (
    cloudflare_pages_deploy,
    cloudflare_tunnel_create,
    cloudflare_tunnel_run,
)
from aura_cli.core.tools.dev_tools import edit_file, find_in_files, tree_view

# --- Filesystem / Dev tools ---
from aura_cli.core.tools.file_system import list_directory, read_file, write_file

# --- Git helpers (natural language) ---
from aura_cli.core.tools.natural_git import (
    extract_commit_message,
    parse_natural_git_command,
    suggest_commit_message,
)

# --- File monitoring ---
from aura_cli.core.tools.nim_integration import check_file_changes

# --- Shell ---
from aura_cli.core.tools.shell import run_shell_command

logger = get_logger(__name__)


def _delegate_to_agi(task: str) -> str:
    """Delegate a complex multi-step task to the AGI agent."""
    return f"Tarefa delegada ao AGI: {task}"


OPS_TOOLS = {
    # --- Git ---
    "git_status": git_status,
    "git_diff": git_diff,
    "git_diff_context": git_diff_context,
    "git_log": git_log,
    "git_branch": git_branch,
    "git_commit": git_commit,
    "git_smart": git_smart,
    "git_commit_smart": git_commit_smart,
    # --- Git helpers ---
    "suggest_commit_message": suggest_commit_message,
    "extract_commit_message": extract_commit_message,
    "parse_natural_git_command": parse_natural_git_command,
    # --- Docker ---
    "docker_ps": docker_ps,
    "docker_images": docker_images,
    "docker_logs": docker_logs,
    "docker_exec": docker_exec,
    "docker_build": docker_build,
    "docker_compose": docker_compose,
    # --- System / Network ---
    "check_service_health": check_service_health,
    "check_port": check_port,
    "system_resources": system_resources,
    "process_info": process_info,
    # --- File monitoring ---
    "check_file_changes": check_file_changes,
    # --- Cloud ---
    "cloudflare_tunnel_create": cloudflare_tunnel_create,
    "cloudflare_tunnel_run": cloudflare_tunnel_run,
    "cloudflare_pages_deploy": cloudflare_pages_deploy,
    # --- CI/CD: GitHub Actions ---
    "gh_create_workflow": gh_create_workflow,
    "gh_get_workflow_status": gh_get_workflow_status,
    "gh_list_workflows": gh_list_workflows,
    "gh_run_workflow": gh_run_workflow,
    # --- Deployment ---
    "deploy_deploy_application": deploy_deploy_application,
    "deploy_get_deployment_status": deploy_get_deployment_status,
    "deploy_check_deployment_health": deploy_check_deployment_health,
    "deploy_rollback_deployment": deploy_rollback_deployment,
    # --- Filesystem / Dev ---
    "run_shell_command": run_shell_command,
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_directory": list_directory,
    "tree_view": tree_view,
    "find_in_files": find_in_files,
    # --- Meta ---
    "delegate_to_agi": _delegate_to_agi,
}


# Advanced ops tools loaded lazily to avoid import overhead at startup
def _load_advanced_ops_tools() -> dict:
    """Load advanced ops tools from core/ops_tools/ modules."""
    advanced = {}
    # Kubernetes
    try:
        from aura_cli.core.ops_tools.infrastructure.kubernetes import KubernetesManager

        _k8s = KubernetesManager()
        advanced.update(
            {
                "k8s_list_pods": _k8s.list_pods,
                "k8s_get_pod_logs": _k8s.get_pod_logs,
                "k8s_apply_manifest": _k8s.apply_manifest,
                "k8s_scale_deployment": _k8s.scale_deployment,
            }
        )
    except Exception as exc:
        logger.debug("Kubernetes tools unavailable: %s", exc)
    # Terraform
    try:
        from aura_cli.core.ops_tools.infrastructure.terraform import TerraformManager

        _tf = TerraformManager()
        advanced.update(
            {
                "terraform_init": _tf.init,
                "terraform_plan": _tf.plan,
                "terraform_apply": _tf.apply,
                "terraform_state": _tf.get_state,
            }
        )
    except Exception as exc:
        logger.debug("Terraform tools unavailable: %s", exc)
    # Security
    try:
        from aura_cli.core.ops_tools.security.security_audit import SecurityAuditor
        from aura_cli.core.ops_tools.security.vulnerability_scanner import (
            VulnerabilityScanner,
        )

        _vs = VulnerabilityScanner()
        _sa = SecurityAuditor()
        advanced.update(
            {
                "security_scan_dependencies": _vs.scan_dependencies,
                "security_scan_code": _vs.scan_code,
                "security_audit": _sa.audit_security,
            }
        )
    except Exception as exc:
        logger.debug("Security tools unavailable: %s", exc)
    # Database
    try:
        from aura_cli.core.ops_tools.database.backup import DatabaseBackup
        from aura_cli.core.ops_tools.database.migration import DatabaseMigration
        from aura_cli.core.ops_tools.database.monitor import DatabaseMonitor

        advanced.update(
            {
                "db_backup": DatabaseBackup().create_backup,
                "db_migrate": DatabaseMigration().apply_all_pending,
                "db_monitor": DatabaseMonitor().collect_metrics,
            }
        )
    except Exception as exc:
        logger.debug("Database tools unavailable: %s", exc)
    # CI/CD (already in main OPS_TOOLS, but included here for 'general' mode completeness)
    try:
        from aura_cli.core.ops_tools.ci_cd.deployment import deploy_application
        from aura_cli.core.ops_tools.ci_cd.github_actions import (
            create_workflow,
            run_workflow,
        )

        advanced.update(
            {
                "cicd_create_workflow": create_workflow,
                "cicd_run_workflow": run_workflow,
                "cicd_deploy": deploy_application,
            }
        )
    except Exception as exc:
        logger.debug("CI/CD tools unavailable: %s", exc)
    return advanced


def get_ops_tools_for_mode(mode: str) -> dict:
    """Return OPS_TOOLS dict filtered/extended for a specific ops mode."""
    base = dict(OPS_TOOLS)
    mode = mode.lower()

    if mode == "git":
        # Git + git helpers + filesystem tools
        git_tools = {
            "git_status",
            "git_diff",
            "git_diff_context",
            "git_log",
            "git_branch",
            "git_commit",
            "git_smart",
            "git_commit_smart",
            "suggest_commit_message",
            "extract_commit_message",
            "parse_natural_git_command",
            "read_file",
            "write_file",
            "edit_file",
            "list_directory",
            "find_in_files",
            "tree_view",
            "run_shell_command",
        }
        return {k: v for k, v in base.items() if k in git_tools}
    elif mode == "docker":
        # Docker + system tools
        docker_tools = {
            "docker_ps",
            "docker_images",
            "docker_logs",
            "docker_exec",
            "docker_build",
            "docker_compose",
            "read_file",
            "write_file",
            "edit_file",
            "list_directory",
            "run_shell_command",
            "system_resources",
            "check_port",
            "check_service_health",
        }
        return {k: v for k, v in base.items() if k in docker_tools}
    elif mode in ("k8s", "kubernetes"):
        adv = _load_advanced_ops_tools()
        base.update({k: v for k, v in adv.items() if k.startswith("k8s_")})
    elif mode == "terraform":
        adv = _load_advanced_ops_tools()
        base.update({k: v for k, v in adv.items() if k.startswith("terraform_")})
    elif mode == "security":
        adv = _load_advanced_ops_tools()
        base.update({k: v for k, v in adv.items() if k.startswith("security_")})
    elif mode == "db":
        adv = _load_advanced_ops_tools()
        base.update({k: v for k, v in adv.items() if k.startswith("db_")})
    elif mode == "cicd":
        # CI/CD mode includes all gh_* and deploy_* tools from base
        adv = _load_advanced_ops_tools()
        base.update({k: v for k, v in adv.items() if k.startswith("cicd_")})
    elif mode == "general":
        base.update(_load_advanced_ops_tools())
    return base


OPS_TOOL_CATEGORIES = {
    "git": [
        "git_status",
        "git_diff",
        "git_diff_context",
        "git_log",
        "git_branch",
        "git_commit",
        "git_smart",
        "git_commit_smart",
        "suggest_commit_message",
        "extract_commit_message",
        "parse_natural_git_command",
    ],
    "docker": [
        "docker_ps",
        "docker_images",
        "docker_logs",
        "docker_exec",
        "docker_build",
        "docker_compose",
    ],
    "system": [
        "check_service_health",
        "check_port",
        "system_resources",
        "process_info",
        "check_file_changes",
    ],
    "cloudflare": [
        "cloudflare_tunnel_create",
        "cloudflare_tunnel_run",
        "cloudflare_pages_deploy",
    ],
    "cicd": [
        "gh_create_workflow",
        "gh_get_workflow_status",
        "gh_list_workflows",
        "gh_run_workflow",
    ],
    "deployment": [
        "deploy_deploy_application",
        "deploy_get_deployment_status",
        "deploy_check_deployment_health",
        "deploy_rollback_deployment",
    ],
}
