"""Cloud tools — registers AWS, GCP and Azure operations as LLM-callable tools.

Read operations (list, describe, status) are always available.
Non-destructive write operations (upload, tag) require the standard tool
confirmation flow.
Destructive operations (terminate, delete) require ``allow_destructive=True``
to be set in the active ``TaskExecutionPolicy``; they are never auto-approved.

Tools exposed:
    cloud_list_resources    — list resources of any type on any provider
    cloud_get_status        — get status of a specific resource
    cloud_ec2_start         — start an EC2 instance (write, non-destructive)
    cloud_ec2_stop          — stop an EC2 instance (write, non-destructive)
    cloud_s3_list_buckets   — list S3 buckets
    cloud_s3_upload         — upload a local file to S3 (write, non-destructive)
    cloud_providers_status  — check which cloud SDKs are configured
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.ops_tools.infrastructure.cloud.aws import AWSManager
from aura_cli.core.ops_tools.infrastructure.cloud.azure import AzureManager
from aura_cli.core.ops_tools.infrastructure.cloud.gcp import GCPManager

logger = get_logger(__name__)

# Lazy-initialized singletons — only created on first use
_aws: Optional[AWSManager] = None
_gcp: Optional[GCPManager] = None
_azure: Optional[AzureManager] = None


def _get_aws() -> AWSManager:
    global _aws
    if _aws is None:
        _aws = AWSManager()
    return _aws


def _get_gcp() -> GCPManager:
    global _gcp
    if _gcp is None:
        _gcp = GCPManager()
    return _gcp


def _get_azure() -> AzureManager:
    global _azure
    if _azure is None:
        _azure = AzureManager()
    return _azure


def _provider_manager(provider: str):
    """Return the manager for *provider* (aws/gcp/azure), or raise ValueError."""
    p = provider.lower().strip()
    if p == "aws":
        return _get_aws()
    if p in ("gcp", "google"):
        return _get_gcp()
    if p in ("azure", "microsoft"):
        return _get_azure()
    raise ValueError(
        f"Unknown cloud provider '{provider}'. Supported: aws, gcp, azure."
    )


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def cloud_providers_status() -> str:
    """Return which cloud provider SDKs are configured and available.

    Returns:
        JSON string with availability status for each provider.
    """
    status: Dict[str, Any] = {}
    for name, mgr_fn in [("aws", _get_aws), ("gcp", _get_gcp), ("azure", _get_azure)]:
        try:
            mgr = mgr_fn()
            available = mgr.is_available()
        except Exception as exc:
            available = False
            logger.debug("Provider %s availability check failed: %s", name, exc)
        status[name] = {"available": available}
    return json.dumps(status, indent=2)


def cloud_list_resources(
    provider: str,
    resource_type: str,
    region: Optional[str] = None,
    **filters: Any,
) -> str:
    """List cloud resources of a given type on a provider.

    Args:
        provider: Cloud provider — ``aws``, ``gcp``, or ``azure``.
        resource_type: Resource type, e.g. ``ec2``, ``s3``, ``compute``, ``vm``.
        region: Optional region/zone override.
        **filters: Provider-specific filter kwargs forwarded to the SDK call.

    Returns:
        JSON string with a list of resource summary dicts.
    """
    try:
        mgr = _provider_manager(provider)
        if not mgr.is_available():
            return json.dumps(
                {"error": f"Provider '{provider}' is not configured or SDK is missing."}
            )
        if region and hasattr(mgr, "_region"):
            mgr._region = region
        resources = mgr.list_resources(resource_type, **filters)
        return json.dumps({"provider": provider, "resource_type": resource_type, "resources": resources}, indent=2)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        logger.error("cloud_list_resources error: %s", exc)
        return json.dumps({"error": f"Unexpected error listing {resource_type} on {provider}: {exc}"})


def cloud_get_status(provider: str, resource_id: str) -> str:
    """Get the current status of a specific cloud resource.

    Args:
        provider: Cloud provider — ``aws``, ``gcp``, or ``azure``.
        resource_id: Resource identifier (instance ID, ARN, resource URI, etc.).

    Returns:
        JSON string with resource status details.
    """
    try:
        mgr = _provider_manager(provider)
        if not mgr.is_available():
            return json.dumps({"error": f"Provider '{provider}' is not configured."})
        status = mgr.get_resource_status(resource_id)
        return json.dumps({"provider": provider, "resource_id": resource_id, "status": status}, indent=2)
    except ValueError as exc:
        return json.dumps({"error": str(exc)})
    except Exception as exc:
        logger.error("cloud_get_status error: %s", exc)
        return json.dumps({"error": f"Unexpected error: {exc}"})


def cloud_ec2_start(instance_id: str) -> str:
    """Start an AWS EC2 instance.

    Args:
        instance_id: EC2 instance ID (e.g. ``i-0abcdef1234567890``).

    Returns:
        JSON string with the operation result.
    """
    try:
        aws = _get_aws()
        if not aws.is_available():
            return json.dumps({"error": "AWS is not configured."})
        result = aws.start_instance(instance_id)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("cloud_ec2_start error: %s", exc)
        return json.dumps({"error": str(exc)})


def cloud_ec2_stop(instance_id: str) -> str:
    """Stop an AWS EC2 instance.

    Args:
        instance_id: EC2 instance ID (e.g. ``i-0abcdef1234567890``).

    Returns:
        JSON string with the operation result.
    """
    try:
        aws = _get_aws()
        if not aws.is_available():
            return json.dumps({"error": "AWS is not configured."})
        result = aws.stop_instance(instance_id)
        return json.dumps(result, indent=2)
    except Exception as exc:
        logger.error("cloud_ec2_stop error: %s", exc)
        return json.dumps({"error": str(exc)})


def cloud_s3_list_buckets() -> str:
    """List all S3 buckets in the configured AWS account.

    Returns:
        JSON string with bucket list.
    """
    return cloud_list_resources("aws", "s3")


def cloud_s3_upload(local_path: str, bucket: str, key: Optional[str] = None) -> str:
    """Upload a local file to an S3 bucket.

    Args:
        local_path: Path to the local file to upload.
        bucket: Target S3 bucket name.
        key: Destination key in the bucket. Defaults to the filename.

    Returns:
        JSON string with upload result.
    """
    try:
        aws = _get_aws()
        if not aws.is_available():
            return json.dumps({"error": "AWS is not configured."})

        session = aws._get_session()
        if session is None:
            return json.dumps({"error": "AWS session could not be established."})

        src = Path(local_path)
        if not src.is_file():
            return json.dumps({"error": f"File not found: {local_path}"})

        dest_key = key or src.name
        s3 = session.client("s3")
        s3.upload_file(str(src), bucket, dest_key)
        return json.dumps(
            {"uploaded": True, "bucket": bucket, "key": dest_key, "size": src.stat().st_size},
            indent=2,
        )
    except Exception as exc:
        logger.error("cloud_s3_upload error: %s", exc)
        return json.dumps({"error": str(exc)})
