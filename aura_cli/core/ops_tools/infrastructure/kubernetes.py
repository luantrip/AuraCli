"""Kubernetes cluster manager for the Ops agent via kubectl.

Wraps kubectl commands for namespace/pod listing, log retrieval, manifest
application and deployment scaling. Requires kubectl in PATH; uses a 30s
timeout by default. Outputs are parsed from kubectl JSON where available.
"""

from dataclasses import dataclass
import json
import subprocess
from typing import List, Optional, Tuple

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


@dataclass
class K8sNamespace:
    """
    Namespace do Kubernetes.

    Attributes:
        name: Nome do namespace
        status: Status
        age: Idade
    """

    name: str
    status: str
    age: str


@dataclass
class K8sResource:
    """
    Recurso do Kubernetes.

    Attributes:
        name: Nome
        namespace: Namespace
        kind: Tipo (Pod, Service, etc.)
        status: Status
        age: Idade
    """

    name: str
    namespace: str
    kind: str
    status: str
    age: str


class KubernetesManager:
    """Manages Kubernetes cluster operations."""

    def __init__(self):
        """Initialise the Kubernetes manager."""
        self.stats = get_stats()

        import shutil

        self.kubectl_available = shutil.which("kubectl") is not None

        if not self.kubectl_available:
            logger.warning(
                "kubectl not found. Kubernetes features limited."
            )
        else:
            logger.info("KubernetesManager initialized")

    def _run_kubectl(self, command: List[str], timeout: int = 30) -> Tuple[bool, str]:
        """Run a kubectl command and return (success, output)."""
        if not self.kubectl_available:
            return False, "kubectl não disponível"

        try:
            result = subprocess.run(
                ["kubectl", *command], capture_output=True, text=True, timeout=timeout
            )

            return result.returncode == 0, (
                result.stdout if result.returncode == 0 else result.stderr
            )

        except subprocess.TimeoutExpired:
            return False, "Timeout ao executar comando"
        except Exception as e:
            return False, str(e)

    def list_namespaces(self) -> List[K8sNamespace]:
        """Return a list of namespaces."""
        success, output = self._run_kubectl(["get", "namespaces", "-o", "json"])

        if not success:
            logger.error(f"Error listing namespaces: {output}")
            return []

        try:
            data = json.loads(output)
            namespaces = []

            for item in data.get("items", []):
                metadata = item.get("metadata", {})
                status = item.get("status", {})

                namespace = K8sNamespace(
                    name=metadata.get("name", ""),
                    status=status.get("phase", "Unknown"),
                    age=self._calculate_age(metadata.get("creationTimestamp", "")),
                )
                namespaces.append(namespace)

            return namespaces

        except Exception as e:
            logger.error(f"Error processing namespaces: {e}", exc_info=True)
            return []

    def list_pods(self, namespace: Optional[str] = None) -> List[K8sResource]:
        """Return a list of pods."""
        cmd = ["get", "pods", "-o", "json"]
        if namespace:
            cmd.extend(["-n", namespace])

        success, output = self._run_kubectl(cmd)

        if not success:
            return []

        try:
            data = json.loads(output)
            pods = []

            for item in data.get("items", []):
                metadata = item.get("metadata", {})
                status = item.get("status", {})

                pod = K8sResource(
                    name=metadata.get("name", ""),
                    namespace=metadata.get("namespace", "default"),
                    kind="Pod",
                    status=status.get("phase", "Unknown"),
                    age=self._calculate_age(metadata.get("creationTimestamp", "")),
                )
                pods.append(pod)

            return pods

        except Exception as e:
            logger.error(f"Error processing pods: {e}", exc_info=True)
            return []

    def get_pod_logs(
        self, pod_name: str, namespace: str = "default", tail: int = 100
    ) -> str:
        """Return logs from a pod."""
        success, output = self._run_kubectl(
            ["logs", pod_name, "-n", namespace, f"--tail={tail}"], timeout=60
        )

        if success:
            return output
        else:
            logger.error(f"Error fetching logs: {output}")
            return f"Erro: {output}"

    def apply_manifest(self, manifest_path: str) -> str:
        """
        Aplica manifest do Kubernetes.

        Args:
            manifest_path: Caminho do manifest

        Returns:
            Mensagem de resultado
        """
        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        display_tool_call("apply_manifest", {"manifest_path": manifest_path})

        success, output = self._run_kubectl(["apply", "-f", manifest_path], timeout=120)

        if success:
            logger.info(f"Manifest {manifest_path} aplicado com sucesso")
            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Manifest aplicado[/{UIStyles.SUCCESS}]"
            )
            self.stats.track_tool_usage("kubernetes_apply")
            return "Manifest aplicado com sucesso"
        else:
            error_msg = f"Error applying manifest: {output}"
            logger.error(error_msg)
            console.print(f"[{UIStyles.ERROR}]{error_msg}[/{UIStyles.ERROR}]")
            return error_msg

    def scale_deployment(
        self, deployment_name: str, replicas: int, namespace: str = "default"
    ) -> str:
        """Scale a deployment to the given replica count."""
        success, output = self._run_kubectl(
            [
                "scale",
                "deployment",
                deployment_name,
                f"--replicas={replicas}",
                "-n",
                namespace,
            ]
        )

        if success:
            return f"Deployment {deployment_name} escalado para {replicas} réplicas"
        else:
            return f"Error scaling: {output}"

    def _calculate_age(self, timestamp: str) -> str:
        """Calculate resource age from a creation timestamp."""
        if not timestamp:
            return "Unknown"

        try:
            from datetime import datetime

            created = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now(created.tzinfo)
            delta = now - created

            days = delta.days
            hours = delta.seconds // 3600
            minutes = (delta.seconds % 3600) // 60

            if days > 0:
                return f"{days}d"
            elif hours > 0:
                return f"{hours}h"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"
