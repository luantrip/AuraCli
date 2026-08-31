"""AWS cloud infrastructure adapter."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from aura_cli.core.logger import get_logger
from aura_cli.core.ops_tools.infrastructure.cloud.base import CloudProviderManager

logger = get_logger(__name__)
console = Console()


class AWSManager(CloudProviderManager):
    """
    AWS Cloud Manager using boto3 SDK.

    Provides comprehensive AWS resource management without CLI dependencies.
    Automatically uses credentials from:
    - Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
    - AWS credentials file (~/.aws/credentials)
    - IAM role (when running on AWS)

    Supported Resource Types:
        - ec2: EC2 instances
        - s3: S3 buckets
        - lambda: Lambda functions
        - rds: RDS database instances
        - ecs: ECS services/tasks
    """

    def __init__(self, region: Optional[str] = None):
        """
        Initialize AWS Manager.

        Args:
            region: AWS region (defaults to AWS_DEFAULT_REGION or us-east-1)
        """
        super().__init__("AWS")
        self._boto3 = None
        self._session = None
        self._region = region
        self._available: Optional[bool] = None

    def _get_boto3(self):
        """Import boto3 (now essential)."""
        if self._boto3 is None:
            import boto3

            self._boto3 = boto3
        return self._boto3

    def _get_session(self):
        """Get or create boto3 session."""
        if self._session is not None:
            return self._session

        boto3 = self._get_boto3()
        if boto3 is None:
            return None

        try:
            import os

            region = self._region or os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
            self._session = boto3.Session(region_name=region)
            sts = self._session.client("sts")
            sts.get_caller_identity()
            logger.debug(f"AWS session created for region {region}")
            return self._session
        except Exception as e:
            logger.warning(f"AWS credentials not configured: {e}")
            self._session = None
            return None

    def is_available(self) -> bool:
        """Check if AWS SDK is available and configured."""
        if self._available is not None:
            return self._available

        self._available = self._get_session() is not None
        return self._available

    def list_resources(self, resource_type: str, **filters) -> List[Dict[str, Any]]:
        """
        List AWS resources.

        Args:
            resource_type: Type (ec2, s3, lambda, rds, ecs)
            **filters: Resource-specific filters

        Returns:
            List of resource dictionaries
        """
        session = self._get_session()
        if session is None:
            logger.warning("AWS not available")
            return []

        resource_handlers = {
            "ec2": self._list_ec2_instances,
            "s3": self._list_s3_buckets,
            "lambda": self._list_lambda_functions,
            "rds": self._list_rds_instances,
            "ecs": self._list_ecs_services,
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

    def _list_ec2_instances(self, **filters) -> List[Dict[str, Any]]:
        session = self._get_session()
        ec2 = session.client("ec2")

        ec2_filters = []
        if "state" in filters:
            ec2_filters.append(
                {"Name": "instance-state-name", "Values": [filters["state"]]}
            )
        if "tag" in filters:
            for key, value in filters["tag"].items():
                ec2_filters.append({"Name": f"tag:{key}", "Values": [value]})

        paginator = ec2.get_paginator("describe_instances")
        page_iterator = paginator.paginate(Filters=ec2_filters if ec2_filters else [])

        instances = []
        for page in page_iterator:
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    name = ""
                    for tag in instance.get("Tags", []):
                        if tag.get("Key") == "Name":
                            name = tag.get("Value", "")
                            break

                    instances.append(
                        {
                            "id": instance.get("InstanceId"),
                            "name": name,
                            "type": instance.get("InstanceType"),
                            "state": instance.get("State", {}).get("Name"),
                            "public_ip": instance.get("PublicIpAddress"),
                            "private_ip": instance.get("PrivateIpAddress"),
                            "launch_time": str(instance.get("LaunchTime", "")),
                            "availability_zone": instance.get("Placement", {}).get(
                                "AvailabilityZone"
                            ),
                        }
                    )

        if instances:
            table = Table(title="☁️ AWS EC2 Instances")
            table.add_column("ID", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Type")
            table.add_column("State")
            table.add_column("Public IP", style="yellow")

            for inst in instances:
                state_style = "green" if inst["state"] == "running" else "red"
                table.add_row(
                    inst["id"],
                    inst["name"],
                    inst["type"],
                    f"[{state_style}]{inst['state']}[/{state_style}]",
                    inst["public_ip"] or "-",
                )

            console.print(table)

        self.stats.track_tool_usage("aws_list_ec2")
        logger.info(f"Listed {len(instances)} EC2 instances")
        return instances

    def _list_s3_buckets(self, **filters) -> List[Dict[str, Any]]:
        """List S3 buckets."""
        session = self._get_session()
        s3 = session.client("s3")

        response = s3.list_buckets()
        buckets = []

        for bucket in response.get("Buckets", []):
            bucket_name = bucket.get("Name")

            try:
                location = s3.get_bucket_location(Bucket=bucket_name)
                region = location.get("LocationConstraint") or "us-east-1"
            except Exception:
                region = "unknown"

            buckets.append(
                {
                    "name": bucket_name,
                    "creation_date": str(bucket.get("CreationDate", "")),
                    "region": region,
                }
            )

        if "prefix" in filters:
            prefix = filters["prefix"]
            buckets = [b for b in buckets if b["name"].startswith(prefix)]

        if buckets:
            table = Table(title="☁️ AWS S3 Buckets")
            table.add_column("Name", style="cyan")
            table.add_column("Region", style="yellow")
            table.add_column("Created")

            for bucket in buckets:
                table.add_row(
                    bucket["name"], bucket["region"], bucket["creation_date"][:10]
                )

            console.print(table)

        self.stats.track_tool_usage("aws_list_s3")
        logger.info(f"Listed {len(buckets)} S3 buckets")
        return buckets

    def _list_lambda_functions(self, **filters) -> List[Dict[str, Any]]:
        """List Lambda functions."""
        session = self._get_session()
        lambda_client = session.client("lambda")

        paginator = lambda_client.get_paginator("list_functions")
        functions = []

        for page in paginator.paginate():
            for func in page.get("Functions", []):
                functions.append(
                    {
                        "name": func.get("FunctionName"),
                        "runtime": func.get("Runtime"),
                        "memory": func.get("MemorySize"),
                        "timeout": func.get("Timeout"),
                        "last_modified": func.get("LastModified"),
                        "code_size": func.get("CodeSize"),
                        "handler": func.get("Handler"),
                    }
                )

        if functions:
            table = Table(title="☁️ AWS Lambda Functions")
            table.add_column("Name", style="cyan")
            table.add_column("Runtime", style="green")
            table.add_column("Memory", style="yellow")
            table.add_column("Timeout")

            for func in functions:
                table.add_row(
                    func["name"],
                    func["runtime"] or "-",
                    f"{func['memory']} MB",
                    f"{func['timeout']}s",
                )

            console.print(table)

        self.stats.track_tool_usage("aws_list_lambda")
        logger.info(f"Listed {len(functions)} Lambda functions")
        return functions

    def _list_rds_instances(self, **filters) -> List[Dict[str, Any]]:
        """List RDS database instances."""
        session = self._get_session()
        rds = session.client("rds")

        paginator = rds.get_paginator("describe_db_instances")
        instances = []

        for page in paginator.paginate():
            for db in page.get("DBInstances", []):
                instances.append(
                    {
                        "id": db.get("DBInstanceIdentifier"),
                        "engine": db.get("Engine"),
                        "engine_version": db.get("EngineVersion"),
                        "instance_class": db.get("DBInstanceClass"),
                        "status": db.get("DBInstanceStatus"),
                        "endpoint": db.get("Endpoint", {}).get("Address"),
                        "port": db.get("Endpoint", {}).get("Port"),
                        "storage_gb": db.get("AllocatedStorage"),
                    }
                )

        if instances:
            table = Table(title="☁️ AWS RDS Instances")
            table.add_column("ID", style="cyan")
            table.add_column("Engine", style="green")
            table.add_column("Class")
            table.add_column("Status")
            table.add_column("Storage")

            for db in instances:
                status_style = "green" if db["status"] == "available" else "yellow"
                table.add_row(
                    db["id"],
                    f"{db['engine']} {db['engine_version']}",
                    db["instance_class"],
                    f"[{status_style}]{db['status']}[/{status_style}]",
                    f"{db['storage_gb']} GB",
                )

            console.print(table)

        self.stats.track_tool_usage("aws_list_rds")
        logger.info(f"Listed {len(instances)} RDS instances")
        return instances

    def _list_ecs_services(
        self, cluster: Optional[str] = None, **filters
    ) -> List[Dict[str, Any]]:
        """List ECS services."""
        session = self._get_session()
        ecs = session.client("ecs")

        services = []

        clusters_response = ecs.list_clusters()
        cluster_arns = clusters_response.get("clusterArns", [])

        if cluster:
            cluster_arns = [arn for arn in cluster_arns if cluster in arn]

        for cluster_arn in cluster_arns:
            services_response = ecs.list_services(cluster=cluster_arn)
            service_arns = services_response.get("serviceArns", [])

            if service_arns:
                describe_response = ecs.describe_services(
                    cluster=cluster_arn, services=service_arns
                )

                for svc in describe_response.get("services", []):
                    services.append(
                        {
                            "name": svc.get("serviceName"),
                            "cluster": cluster_arn.split("/")[-1],
                            "status": svc.get("status"),
                            "running_count": svc.get("runningCount"),
                            "desired_count": svc.get("desiredCount"),
                            "task_definition": svc.get("taskDefinition", "").split("/")[
                                -1
                            ],
                        }
                    )

        if services:
            table = Table(title="☁️ AWS ECS Services")
            table.add_column("Service", style="cyan")
            table.add_column("Cluster", style="green")
            table.add_column("Status")
            table.add_column("Running/Desired")

            for svc in services:
                status_style = "green" if svc["status"] == "ACTIVE" else "yellow"
                table.add_row(
                    svc["name"],
                    svc["cluster"],
                    f"[{status_style}]{svc['status']}[/{status_style}]",
                    f"{svc['running_count']}/{svc['desired_count']}",
                )

            console.print(table)

        self.stats.track_tool_usage("aws_list_ecs")
        logger.info(f"Listed {len(services)} ECS services")
        return services

    def get_resource_status(self, resource_id: str) -> Dict[str, Any]:
        """
        Get status of a specific AWS resource.

        Automatically detects resource type from ID format.

        Args:
            resource_id: Resource ID (e.g., i-xxx for EC2, arn:aws:lambda:...)

        Returns:
            Status dictionary
        """
        session = self._get_session()
        if session is None:
            return {
                "resource_id": resource_id,
                "status": "unavailable",
                "error": "AWS not configured",
            }

        try:
            if resource_id.startswith("i-"):
                return self._get_ec2_status(resource_id)
            elif resource_id.startswith("arn:aws:lambda"):
                return self._get_lambda_status(resource_id)
            elif resource_id.startswith("arn:aws:rds"):
                return self._get_rds_status(resource_id)
            else:
                return self._get_ec2_status(resource_id)

        except Exception as e:
            logger.error(f"Error getting status for {resource_id}: {e}")
            return {
                "resource_id": resource_id,
                "status": "error",
                "error": str(e),
                "provider": "aws",
            }

    def _get_ec2_status(self, instance_id: str) -> Dict[str, Any]:
        """Get EC2 instance status."""
        session = self._get_session()
        ec2 = session.client("ec2")

        response = ec2.describe_instances(InstanceIds=[instance_id])

        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                return {
                    "resource_id": instance_id,
                    "resource_type": "ec2",
                    "status": instance.get("State", {}).get("Name"),
                    "instance_type": instance.get("InstanceType"),
                    "public_ip": instance.get("PublicIpAddress"),
                    "private_ip": instance.get("PrivateIpAddress"),
                    "provider": "aws",
                }

        return {"resource_id": instance_id, "status": "not_found", "provider": "aws"}

    def _get_lambda_status(self, function_arn: str) -> Dict[str, Any]:
        """Get Lambda function status."""
        session = self._get_session()
        lambda_client = session.client("lambda")

        func_name = function_arn.split(":")[-1] if ":" in function_arn else function_arn

        response = lambda_client.get_function(FunctionName=func_name)
        config = response.get("Configuration", {})

        return {
            "resource_id": function_arn,
            "resource_type": "lambda",
            "status": config.get("State", "unknown"),
            "runtime": config.get("Runtime"),
            "memory": config.get("MemorySize"),
            "last_modified": config.get("LastModified"),
            "provider": "aws",
        }

    def _get_rds_status(self, db_identifier: str) -> Dict[str, Any]:
        """Get RDS instance status."""
        session = self._get_session()
        rds = session.client("rds")

        if ":" in db_identifier:
            db_identifier = db_identifier.split(":")[-1]

        response = rds.describe_db_instances(DBInstanceIdentifier=db_identifier)

        for db in response.get("DBInstances", []):
            return {
                "resource_id": db_identifier,
                "resource_type": "rds",
                "status": db.get("DBInstanceStatus"),
                "engine": db.get("Engine"),
                "endpoint": db.get("Endpoint", {}).get("Address"),
                "provider": "aws",
            }

        return {"resource_id": db_identifier, "status": "not_found", "provider": "aws"}

    def start_instance(self, instance_id: str) -> Dict[str, Any]:
        """Start an EC2 instance."""
        session = self._get_session()
        if session is None:
            return {"status": "error", "error": "AWS not configured"}

        ec2 = session.client("ec2")
        try:
            ec2.start_instances(InstanceIds=[instance_id])
            logger.info(f"Started EC2 instance: {instance_id}")
            console.print(f"[green]✅ Started instance {instance_id}[/green]")
            return {"status": "starting", "instance_id": instance_id}
        except Exception as e:
            logger.error(f"Error starting instance: {e}")
            return {"status": "error", "error": str(e)}

    def stop_instance(self, instance_id: str) -> Dict[str, Any]:
        """Stop an EC2 instance."""
        session = self._get_session()
        if session is None:
            return {"status": "error", "error": "AWS not configured"}

        ec2 = session.client("ec2")
        try:
            ec2.stop_instances(InstanceIds=[instance_id])
            logger.info(f"Stopped EC2 instance: {instance_id}")
            console.print(f"[yellow]⏹️ Stopped instance {instance_id}[/yellow]")
            return {"status": "stopping", "instance_id": instance_id}
        except Exception as e:
            logger.error(f"Error stopping instance: {e}")
            return {"status": "error", "error": str(e)}


__all__ = ["AWSManager"]
