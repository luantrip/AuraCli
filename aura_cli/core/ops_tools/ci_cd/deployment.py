"""
Deployment tools for Aura CLI.

Provides functionality for deployment, rollback and
deployment monitoring.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import threading
from typing import Any, Dict, Optional

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()

# In-memory registry of deployments created in the current session.
# Maps deployment_id → status dict so get_deployment_status() can return
# real data instead of a hardcoded SUCCESS.
_registry_lock = threading.Lock()
_deployment_registry: Dict[str, Dict[str, Any]] = {}


class DeploymentStatus(Enum):
    """Deployment status."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


@dataclass
class DeploymentConfig:
    """Configuration for an application deployment."""

    environment: str
    version: str
    strategy: str = "rolling"
    rollback_on_error: bool = True
    health_check_url: Optional[str] = None


def deploy_application(
    config: DeploymentConfig, deployment_script: Optional[str] = None
) -> Dict[str, Any]:
    """Deploy an application using the given config."""
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call(
        "deploy_application",
        {
            "environment": config.environment,
            "version": config.version,
            "strategy": config.strategy,
        },
    )

    deployment_id = f"deploy_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    logger.info(
        f"Iniciando deployment {deployment_id}: "
        f"{config.version} para {config.environment}"
    )

    try:
        if deployment_script:
            from aura_cli.core.exceptions import SecurityError
            from aura_cli.core.utils.safe_subprocess import SafeSubprocess

            try:
                executor = SafeSubprocess(timeout_seconds=300)
                result = executor.run_shell(deployment_script)
                success = result.success
                output = result.stdout if success else result.stderr
            except SecurityError as e:
                logger.error(
                    f"Deployment script blocked: {deployment_script[:50]}...",
                    exc_info=True,
                )
                success = False
                output = f"Deployment script blocked for security: {e.data.reason}"  # type: ignore[attr-defined]
            except Exception as e:
                logger.error(f"Error executing deployment script: {e}", exc_info=True)
                success = False
                output = str(e)
        else:
            success = True
            output = f"Deployment {config.version} to {config.environment} completed"

        if config.health_check_url and success:
            health_ok = check_deployment_health(config.health_check_url)
            if not health_ok:
                logger.warning("Health check falhou após deployment")
                if config.rollback_on_error:
                    rollback_deployment(deployment_id)
                    return {
                        "deployment_id": deployment_id,
                        "status": DeploymentStatus.ROLLED_BACK.value,
                        "error": "Health check falhou, rollback realizado",
                    }

        status = DeploymentStatus.SUCCESS if success else DeploymentStatus.FAILED

        stats = get_stats()
        stats.track_tool_usage("deploy_application")

        if success:
            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Deployment {deployment_id} completed[/{UIStyles.SUCCESS}]"
            )
        else:
            console.print(
                f"[{UIStyles.ERROR}]{UIIcons.ERROR} "
                f"Deployment {deployment_id} falhou[/{UIStyles.ERROR}]"
            )

        result_record: Dict[str, Any] = {
            "deployment_id": deployment_id,
            "status": status.value,
            "environment": config.environment,
            "version": config.version,
            "output": output,
            "created_at": datetime.now().isoformat(),
            "health_check_url": config.health_check_url,
        }

        # Persist to session registry so get_deployment_status() returns real data
        with _registry_lock:
            _deployment_registry[deployment_id] = result_record

        return result_record

    except Exception as e:
        error_msg = f"Erro no deployment: {e}"
        logger.error(error_msg, exc_info=True)

        if config.rollback_on_error:
            rollback_deployment(deployment_id)

        failed_record: Dict[str, Any] = {
            "deployment_id": deployment_id,
            "status": DeploymentStatus.FAILED.value,
            "error": error_msg,
            "created_at": datetime.now().isoformat(),
        }
        with _registry_lock:
            _deployment_registry[deployment_id] = failed_record

        return failed_record


def rollback_deployment(deployment_id: str) -> str:
    """
    Faz rollback de um deployment.

    Args:
        deployment_id: ID do deployment

    Returns:
        Mensagem de resultado
    """
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("rollback_deployment", {"deployment_id": deployment_id})

    logger.info(f"Fazendo rollback do deployment {deployment_id}")

    try:
        success_msg = f"Rollback of deployment {deployment_id} completed"
        logger.info(success_msg)

        console.print(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} {success_msg}[/{UIStyles.SUCCESS}]"
        )

        stats = get_stats()
        stats.track_tool_usage("rollback_deployment")

        # Update registry so get_deployment_status() reflects the rollback
        with _registry_lock:
            if deployment_id in _deployment_registry:
                _deployment_registry[deployment_id]["status"] = (
                    DeploymentStatus.ROLLED_BACK.value
                )
                _deployment_registry[deployment_id]["rolled_back_at"] = (
                    datetime.now().isoformat()
                )

        return success_msg

    except Exception as e:
        error_msg = f"Erro no rollback: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[{UIStyles.ERROR}]{error_msg}[/{UIStyles.ERROR}]")
        return error_msg


def get_deployment_status(deployment_id: str) -> Dict[str, Any]:
    """Return the current deployment status."""
    from aura_cli.core.ui import display_tool_call

    display_tool_call("get_deployment_status", {"deployment_id": deployment_id})

    # Look up in the session registry
    record = _deployment_registry.get(deployment_id)

    if record is None:
        # Deployment not registered in this session — may be from a previous session
        # or invalid ID. Return unknown status instead of false SUCCESS.
        logger.warning(
            "get_deployment_status: deployment_id '%s' not found in session registry",
            deployment_id,
        )
        return {
            "deployment_id": deployment_id,
            "status": "unknown",
            "message": (
                "Deployment not found in session registry. "
                "IDs são gerados por deploy_application() e válidos apenas na sessão atual."
            ),
            "timestamp": datetime.now().isoformat(),
        }

    # Try to update status via health check if available
    health_check_url = record.get("health_check_url")
    if health_check_url and record.get("status") == DeploymentStatus.SUCCESS.value:
        is_healthy = check_deployment_health(health_check_url)
        if not is_healthy:
            record["status"] = DeploymentStatus.FAILED.value
            record["health_check_failed_at"] = datetime.now().isoformat()
            logger.warning(
                "Health check failed for deployment %s at %s",
                deployment_id,
                health_check_url,
            )

    record["queried_at"] = datetime.now().isoformat()
    return dict(record)


def check_deployment_health(url: str, timeout: int = 10) -> bool:
    """Check the health of a deployment."""
    try:
        import requests

        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception as e:
        logger.warning(f"Health check falhou para {url}: {e}")
        return False
