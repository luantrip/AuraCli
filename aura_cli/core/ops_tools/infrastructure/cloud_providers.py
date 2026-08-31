"""Cloud provider managers using official SDKs (not CLI wrappers).

Re-exports AWSManager (boto3), GCPManager (google-cloud), AzureManager
(azure-identity/azure-mgmt) and the abstract CloudProviderManager base.
GCP and Azure SDKs are optional — import errors are handled at use-time.
"""

from aura_cli.core.ops_tools.infrastructure.cloud.aws import AWSManager as AWSManager
from aura_cli.core.ops_tools.infrastructure.cloud.azure import (
    AzureManager as AzureManager,
)
from aura_cli.core.ops_tools.infrastructure.cloud.base import CloudProviderManager
from aura_cli.core.ops_tools.infrastructure.cloud.gcp import GCPManager as GCPManager

__all__ = ["AWSManager", "AzureManager", "CloudProviderManager", "GCPManager"]
