"""Azure cloud infrastructure adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.ops_tools.infrastructure.cloud.base import CloudProviderManager

logger = get_logger(__name__)


class AzureManager(CloudProviderManager):
    """
    Azure Cloud Manager.

    Uses azure-identity and azure-mgmt SDK for resource management.
    Automatically uses credentials from:
    - Environment variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)
    - Azure CLI credentials
    - Managed Identity (when running on Azure)

    Supported Resource Types:
        - vm: Virtual Machines
        - storage: Storage Accounts
        - appservice: App Services
    """

    def __init__(self, subscription_id: Optional[str] = None):
        """
        Initialize Azure Manager.

        Args:
            subscription_id: Azure subscription ID (defaults to credential default)
        """
        super().__init__("Azure")
        self._subscription_id = subscription_id
        self._available: Optional[bool] = None
        self._credentials = None

    def _get_credentials(self):
        """Get or validate Azure credentials."""
        if self._credentials is not None:
            return self._credentials

        try:
            from azure.core.exceptions import ClientAuthenticationError
            from azure.identity import DefaultAzureCredential as _DefaultAzureCredential

            credential = _DefaultAzureCredential()
            try:
                credential.get_token("https://management.azure.com/.default")
                self._credentials = credential
                logger.debug("Azure credentials validated")
                return credential
            except ClientAuthenticationError as e:
                logger.debug(f"Azure credentials not configured: {e}")
                self._credentials = None
                return None
        except ImportError:
            logger.debug("azure-identity not installed")
            self._credentials = None
            return None
        except Exception as e:
            logger.warning(f"Error validating Azure credentials: {e}")
            self._credentials = None
            return None

    def _sdk_installed(self) -> bool:
        """Whether the Azure SDK is importable (independent of credentials)."""
        import importlib.util
        return importlib.util.find_spec("azure.identity") is not None

    def availability_error(self) -> str | None:
        """Actionable reason the Azure provider is unavailable, or None if ready."""
        if self.is_available():
            return None
        if not self._sdk_installed():
            return (
                "Azure SDK not installed. Install it with: "
                "pip install azure-identity azure-mgmt-compute"
            )
        return (
            "Azure credentials not configured. Run 'az login' or set "
            "AZURE_CLIENT_ID / AZURE_TENANT_ID / AZURE_CLIENT_SECRET."
        )

    def is_available(self) -> bool:
        """Check if Azure SDK is available and credentials are configured."""
        if self._available is not None:
            return self._available

        if not self._sdk_installed():
            logger.debug("azure-identity not installed")
            self._available = False
            return self._available

        self._available = self._get_credentials() is not None
        return self._available

    def list_resources(self, resource_type: str, **filters) -> List[Dict[str, Any]]:
        """
        List Azure resources.

        Args:
            resource_type: Type (vm, storage, appservice)
            **filters: Resource-specific filters

        Returns:
            List of resource dictionaries
        """
        if not self.is_available():
            logger.warning("Azure SDK not available")
            return []

        resource_handlers = {
            "vm": self._list_virtual_machines,
            "storage": self._list_storage_accounts,
            "appservice": self._list_app_services,
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

    def _list_virtual_machines(
        self, resource_group: Optional[str] = None, **filters
    ) -> List[Dict[str, Any]]:
        """List Virtual Machines."""
        try:
            from azure.mgmt.compute import ComputeManagementClient

            credentials = self._get_credentials()
            if credentials is None:
                return []

            if self._subscription_id is None:
                logger.warning("Azure subscription ID not configured")
                return []

            client = ComputeManagementClient(credentials, self._subscription_id)
            vms = []

            if resource_group:
                resource_groups = [resource_group]
            else:
                from azure.mgmt.resource import ResourceManagementClient

                rg_client = ResourceManagementClient(credentials, self._subscription_id)
                resource_groups = [rg.name for rg in rg_client.resource_groups.list()]

            for rg_name in resource_groups:
                try:
                    vm_list = client.virtual_machines.list(resource_group_name=rg_name)
                    for vm in vm_list:
                        vm_status = None
                        try:
                            instance_view = client.virtual_machines.instance_view(
                                resource_group_name=rg_name, vm_name=vm.name
                            )
                            vm_status = (
                                instance_view.statuses[-1].display_status
                                if instance_view.statuses
                                else None
                            )
                        except Exception as _e:
                            logger.debug(f"Ignorado: {_e}")

                        vms.append(
                            {
                                "name": vm.name,
                                "resource_group": rg_name,
                                "location": vm.location,
                                "vm_size": vm.hardware_profile.vm_size
                                if vm.hardware_profile
                                else None,
                                "status": vm_status or "unknown",
                                "os_type": vm.storage_profile.os_disk.os_type.value
                                if vm.storage_profile and vm.storage_profile.os_disk
                                else None,
                            }
                        )
                except Exception as e:
                    logger.debug(f"Error listing VMs in resource group {rg_name}: {e}")

            self.stats.track_tool_usage("azure_list_vm")
            logger.info(f"Listed {len(vms)} Virtual Machines")
            return vms
        except Exception as e:
            logger.error(f"Error listing Virtual Machines: {e}", exc_info=True)
            return []

    def _list_storage_accounts(self, **filters) -> List[Dict[str, Any]]:
        """List Storage Accounts."""
        try:
            from azure.mgmt.storage import StorageManagementClient

            credentials = self._get_credentials()
            if credentials is None:
                return []

            if self._subscription_id is None:
                logger.warning("Azure subscription ID not configured")
                return []

            client = StorageManagementClient(credentials, self._subscription_id)
            accounts = []

            for account in client.storage_accounts.list():
                accounts.append(
                    {
                        "name": account.name,
                        "resource_group": account.id.split("/")[4]
                        if "/" in account.id
                        else None,
                        "location": account.location,
                        "sku": account.sku.name.value if account.sku else None,
                        "kind": account.kind.value if account.kind else None,
                    }
                )

            self.stats.track_tool_usage("azure_list_storage")
            logger.info(f"Listed {len(accounts)} Storage Accounts")
            return accounts
        except Exception as e:
            logger.error(f"Error listing Storage Accounts: {e}", exc_info=True)
            return []

    def _list_app_services(self, **filters) -> List[Dict[str, Any]]:
        """List App Services."""
        try:
            from azure.mgmt.web import WebSiteManagementClient

            credentials = self._get_credentials()
            if credentials is None:
                return []

            if self._subscription_id is None:
                logger.warning("Azure subscription ID not configured")
                return []

            client = WebSiteManagementClient(credentials, self._subscription_id)
            apps = []

            for app in client.web_apps.list_all():
                apps.append(
                    {
                        "name": app.name,
                        "resource_group": app.resource_group,
                        "location": app.location,
                        "state": app.state,
                        "default_host_name": app.default_host_name,
                    }
                )

            self.stats.track_tool_usage("azure_list_appservice")
            logger.info(f"Listed {len(apps)} App Services")
            return apps
        except Exception as e:
            logger.error(f"Error listing App Services: {e}", exc_info=True)
            return []

    def get_resource_status(self, resource_id: str) -> Dict[str, Any]:
        """
        Get status of a specific Azure resource.

        Args:
            resource_id: Resource ID or name

        Returns:
            Status dictionary
        """
        if not self.is_available():
            return {
                "resource_id": resource_id,
                "status": "unavailable",
                "error": "Azure not configured",
                "provider": "azure",
            }

        try:
            from azure.mgmt.compute import ComputeManagementClient

            credentials = self._get_credentials()
            if credentials is None or self._subscription_id is None:
                return {
                    "resource_id": resource_id,
                    "status": "error",
                    "error": "Azure credentials or subscription not configured",
                    "provider": "azure",
                }

            client = ComputeManagementClient(credentials, self._subscription_id)

            parts = resource_id.split("/")
            if len(parts) >= 2:
                resource_group = parts[-2]
                vm_name = parts[-1]
            else:
                return {
                    "resource_id": resource_id,
                    "status": "error",
                    "error": "Invalid resource ID format",
                    "provider": "azure",
                }

            instance_view = client.virtual_machines.instance_view(
                resource_group_name=resource_group, vm_name=vm_name
            )

            status = (
                instance_view.statuses[-1].display_status
                if instance_view.statuses
                else "unknown"
            )

            return {
                "resource_id": resource_id,
                "resource_type": "vm",
                "status": status,
                "resource_group": resource_group,
                "provider": "azure",
            }
        except Exception as e:
            logger.error(f"Error getting Azure resource status: {e}")
            return {
                "resource_id": resource_id,
                "status": "error",
                "error": str(e),
                "provider": "azure",
            }


__all__ = ["AzureManager"]
