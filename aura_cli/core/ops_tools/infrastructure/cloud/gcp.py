"""Google Cloud infrastructure adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from aura_cli.core.logger import get_logger
from aura_cli.core.ops_tools.infrastructure.cloud.base import CloudProviderManager

logger = get_logger(__name__)
console = Console()


class GCPManager(CloudProviderManager):
    """
    GCP Cloud Manager.

    Uses google-cloud SDK for resource management.
    Automatically uses credentials from:
    - Application Default Credentials (ADC)
    - Service account key file (GOOGLE_APPLICATION_CREDENTIALS)
    - gcloud CLI credentials

    Supported Resource Types:
        - compute: Compute Engine instances
        - storage: Cloud Storage buckets
        - functions: Cloud Functions
    """

    def __init__(self, project: Optional[str] = None):
        """
        Initialize GCP Manager.

        Args:
            project: GCP project ID (defaults to ADC project)
        """
        super().__init__("GCP")
        self._project = project
        self._available: Optional[bool] = None
        self._credentials = None

    def _get_credentials(self):
        """Get or validate GCP credentials."""
        if self._credentials is not None:
            return self._credentials

        try:
            from google.auth import default
            from google.auth.exceptions import DefaultCredentialsError

            credentials, project = default()
            if self._project is None:
                self._project = project

            self._credentials = credentials
            logger.debug(f"GCP credentials validated for project: {self._project}")
            return credentials
        except DefaultCredentialsError as e:
            logger.debug(f"GCP credentials not configured: {e}")
            self._credentials = None
            return None
        except Exception as e:
            logger.warning(f"Error validating GCP credentials: {e}")
            self._credentials = None
            return None

    def is_available(self) -> bool:
        """Check if GCP SDK is available and credentials are configured."""
        if self._available is not None:
            return self._available

        try:
            from google.cloud import compute_v1 as _compute_v1

            self._available = (
                _compute_v1 is not None and self._get_credentials() is not None
            )
        except ImportError:
            logger.debug("google-cloud-compute not installed")
            self._available = False

        return self._available

    def list_resources(self, resource_type: str, **filters) -> List[Dict[str, Any]]:
        """
        List GCP resources.

        Args:
            resource_type: Type (compute, storage, functions)
            **filters: Resource-specific filters

        Returns:
            List of resource dictionaries
        """
        if not self.is_available():
            logger.warning("GCP SDK not available")
            return []

        resource_handlers = {
            "compute": self._list_compute_instances,
            "storage": self._list_storage_buckets,
            "functions": self._list_cloud_functions,
        }

        handler = resource_handlers.get(resource_type.lower())
        if handler is None:
            logger.warning(f"Resource type '{resource_type}' not supported")
            return []

        try:
            return handler(**filters)
        except Exception as e:
            logger.error(f"Error listing {resource_type}: {e}", exc_info=True)
            return []

    def _list_compute_instances(
        self, zone: Optional[str] = None, **filters
    ) -> List[Dict[str, Any]]:
        """List Compute Engine instances."""
        try:
            from google.cloud import compute_v1

            credentials = self._get_credentials()
            if credentials is None:
                return []

            client = compute_v1.InstancesClient(credentials=credentials)
            project = self._project

            instances = []
            if zone:
                zones = [zone]
            else:
                zones_client = compute_v1.ZonesClient(credentials=credentials)
                zones_list = zones_client.list(project=project)
                zones = [zone.name for zone in zones_list]

            for zone_name in zones:
                try:
                    request = compute_v1.ListInstancesRequest(
                        project=project, zone=zone_name
                    )
                    response = client.list(request=request)

                    for instance in response:
                        instances.append(
                            {
                                "id": instance.id,
                                "name": instance.name,
                                "zone": zone_name,
                                "machine_type": instance.machine_type.split("/")[-1],
                                "status": instance.status,
                                "internal_ip": instance.network_interfaces[
                                    0
                                ].network_i_p
                                if instance.network_interfaces
                                else None,
                                "external_ip": instance.network_interfaces[0]
                                .access_configs[0]
                                .nat_i_p
                                if instance.network_interfaces
                                and instance.network_interfaces[0].access_configs
                                else None,
                                "creation_timestamp": instance.creation_timestamp,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Error listing instances in zone {zone_name}: {e}")

            if instances:
                table = Table(title="☁️ GCP Compute Instances")
                table.add_column("Name", style="cyan")
                table.add_column("Zone", style="green")
                table.add_column("Type")
                table.add_column("Status")
                table.add_column("External IP", style="yellow")

                for inst in instances:
                    status_style = "green" if inst["status"] == "RUNNING" else "red"
                    table.add_row(
                        inst["name"],
                        inst["zone"],
                        inst["machine_type"],
                        f"[{status_style}]{inst['status']}[/{status_style}]",
                        inst["external_ip"] or "-",
                    )

                console.print(table)

            self.stats.track_tool_usage("gcp_list_compute")
            logger.info(f"Listed {len(instances)} Compute instances")
            return instances
        except Exception as e:
            logger.error(f"Error listing Compute instances: {e}", exc_info=True)
            return []

    def _list_storage_buckets(self, **filters) -> List[Dict[str, Any]]:
        """List Cloud Storage buckets."""
        try:
            from google.cloud import storage

            credentials = self._get_credentials()
            if credentials is None:
                return []

            client = storage.Client(credentials=credentials, project=self._project)
            buckets = []

            for bucket in client.list_buckets():
                buckets.append(
                    {
                        "name": bucket.name,
                        "location": bucket.location or "unknown",
                        "storage_class": bucket.storage_class,
                        "created": bucket.time_created.isoformat()
                        if bucket.time_created
                        else None,
                    }
                )

            if buckets:
                table = Table(title="☁️ GCP Storage Buckets")
                table.add_column("Name", style="cyan")
                table.add_column("Location", style="yellow")
                table.add_column("Storage Class")

                for bucket in buckets:
                    table.add_row(
                        bucket["name"],
                        bucket["location"],
                        bucket["storage_class"] or "-",
                    )

                console.print(table)

            self.stats.track_tool_usage("gcp_list_storage")
            logger.info(f"Listed {len(buckets)} Storage buckets")
            return buckets
        except Exception as e:
            logger.error(f"Error listing Storage buckets: {e}", exc_info=True)
            return []

    def _list_cloud_functions(self, **filters) -> List[Dict[str, Any]]:
        """List Cloud Functions."""
        try:
            from google.cloud import functions_v1

            credentials = self._get_credentials()
            if credentials is None:
                return []

            client = functions_v1.CloudFunctionsServiceClient(credentials=credentials)
            parent = f"projects/{self._project}/locations/-"

            functions = []
            request = functions_v1.ListFunctionsRequest(parent=parent)
            page_result = client.list_functions(request=request)

            for func in page_result:
                functions.append(
                    {
                        "name": func.name.split("/")[-1],
                        "runtime": func.runtime,
                        "status": func.status.name if func.status else "UNKNOWN",
                        "update_time": func.update_time.isoformat()
                        if func.update_time
                        else None,
                        "available_memory_mb": func.available_memory_mb,
                        "timeout": func.timeout.seconds if func.timeout else None,
                    }
                )

            if functions:
                table = Table(title="☁️ GCP Cloud Functions")
                table.add_column("Name", style="cyan")
                table.add_column("Runtime", style="green")
                table.add_column("Status")
                table.add_column("Memory")

                for func in functions:
                    status_style = "green" if func["status"] == "ACTIVE" else "yellow"
                    table.add_row(
                        func["name"],
                        func["runtime"] or "-",
                        f"[{status_style}]{func['status']}[/{status_style}]",
                        f"{func['available_memory_mb']} MB"
                        if func["available_memory_mb"]
                        else "-",
                    )

                console.print(table)

            self.stats.track_tool_usage("gcp_list_functions")
            logger.info(f"Listed {len(functions)} Cloud Functions")
            return functions
        except Exception as e:
            logger.error(f"Error listing Cloud Functions: {e}", exc_info=True)
            return []

    def get_resource_status(self, resource_id: str) -> Dict[str, Any]:
        """
        Get status of a specific GCP resource.

        Args:
            resource_id: Resource ID or name

        Returns:
            Status dictionary
        """
        if not self.is_available():
            return {
                "resource_id": resource_id,
                "status": "unavailable",
                "error": "GCP not configured",
                "provider": "gcp",
            }

        try:
            from google.cloud import compute_v1

            credentials = self._get_credentials()
            client = compute_v1.InstancesClient(credentials=credentials)
            project = self._project

            parts = resource_id.split("/")
            if len(parts) >= 3:
                zone = parts[-2]
                instance_name = parts[-1]
            else:
                return {
                    "resource_id": resource_id,
                    "status": "error",
                    "error": "Invalid resource ID format",
                    "provider": "gcp",
                }

            request = compute_v1.GetInstanceRequest(
                project=project, zone=zone, instance=instance_name
            )
            instance = client.get(request=request)

            return {
                "resource_id": resource_id,
                "resource_type": "compute",
                "status": instance.status,
                "machine_type": instance.machine_type.split("/")[-1],
                "zone": zone,
                "provider": "gcp",
            }
        except Exception as e:
            logger.error(f"Error getting GCP resource status: {e}")
            return {
                "resource_id": resource_id,
                "status": "error",
                "error": str(e),
                "provider": "gcp",
            }


__all__ = ["GCPManager"]
