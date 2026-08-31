"""
GitHub Actions integration for Aura CLI.

Provides functionality to create, list and execute
GitHub Actions workflows.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from rich.console import Console
import yaml

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


@dataclass
class WorkflowConfig:
    """GitHub Actions workflow configuration."""

    name: str
    on: Dict[str, Any]
    jobs: Dict[str, Any]
    env: Dict[str, Any] = field(default_factory=dict)


def create_workflow(
    workflow_name: str, config: WorkflowConfig, path: str = ".github/workflows"
) -> str:
    """Create a GitHub Actions workflow file."""
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("create_workflow", {"workflow_name": workflow_name, "path": path})

    workflow_dir = Path(path)
    workflow_dir.mkdir(parents=True, exist_ok=True)

    workflow_content = {"name": config.name, "on": config.on, "jobs": config.jobs}

    if config.env:
        workflow_content["env"] = config.env

    workflow_file = workflow_dir / f"{workflow_name}.yml"

    try:
        with open(workflow_file, "w", encoding="utf-8") as f:
            yaml.dump(workflow_content, f, default_flow_style=False, sort_keys=False)

        stats = get_stats()
        stats.track_tool_usage("create_workflow")

        logger.info(f"Workflow '{workflow_name}' created at {workflow_file}")

        console.print(
            f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
            f"Workflow '{workflow_name}' created[/{UIStyles.SUCCESS}]"
        )

        return str(workflow_file)

    except Exception as e:
        error_msg = f"Error creating workflow: {e}"
        logger.error(error_msg, exc_info=True)
        console.print(f"[{UIStyles.ERROR}]{error_msg}[/{UIStyles.ERROR}]")
        return error_msg


def list_workflows(path: str = ".github/workflows") -> List[Dict[str, Any]]:
    """Return a list of existing workflows."""
    workflows: list[Any] = []
    workflow_dir = Path(path)

    if not workflow_dir.exists():
        return workflows

    for workflow_file in workflow_dir.glob("*.yml"):
        try:
            with open(workflow_file, encoding="utf-8") as f:
                content = yaml.safe_load(f)

            workflows.append(
                {
                    "file": str(workflow_file),
                    "name": content.get("name", workflow_file.stem),
                    "on": content.get("on", {}),
                    "jobs": list(content.get("jobs", {}).keys()),
                }
            )
        except Exception as e:
            logger.warning(f"Error reading workflow {workflow_file}: {e}")

    logger.info(f"Encontrados {len(workflows)} workflows")

    return workflows


def run_workflow(
    workflow_name: str, ref: str = "main", inputs: Optional[Dict[str, str]] = None
) -> str:
    """Trigger a workflow run via GitHub CLI."""
    from aura_cli.core.ui import display_tool_call
    from aura_cli.core.ui_bridge import UIIcons, UIStyles

    display_tool_call("run_workflow", {"workflow_name": workflow_name, "ref": ref})

    import shutil

    if not shutil.which("gh"):
        error_msg = "GitHub CLI (gh) not found. Install it to run workflows."
        logger.error(error_msg)
        console.print(f"[{UIStyles.ERROR}]{error_msg}[/{UIStyles.ERROR}]")
        return error_msg

    cmd = ["gh", "workflow", "run", workflow_name, "--ref", ref]

    if inputs:
        for key, value in inputs.items():
            cmd.extend(["-f", f"{key}={value}"])

    import subprocess

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            success_msg = f"Workflow '{workflow_name}' disparado com sucesso"
            logger.info(success_msg)
            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} {success_msg}[/{UIStyles.SUCCESS}]"
            )

            stats = get_stats()
            stats.track_tool_usage("run_workflow")

            return success_msg
        else:
            error_msg = f"Error running workflow: {result.stderr}"
            logger.error(error_msg)
            console.print(f"[{UIStyles.ERROR}]{error_msg}[/{UIStyles.ERROR}]")
            return error_msg

    except subprocess.TimeoutExpired:
        error_msg = "Timeout ao executar workflow"
        logger.error(error_msg)
        return error_msg
    except Exception as e:
        error_msg = f"Error running workflow: {e}"
        logger.error(error_msg, exc_info=True)
        return error_msg


def get_workflow_status(workflow_name: Optional[str] = None) -> List[Dict[str, Any]]:
    """Return the status of one or all workflows."""
    import shutil

    if not shutil.which("gh"):
        logger.warning("GitHub CLI not found")
        return []

    import subprocess

    cmd = ["gh", "run", "list", "--limit", "10"]
    if workflow_name:
        cmd.extend(["--workflow", workflow_name])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            runs = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        runs.append(
                            {
                                "workflow": parts[0],
                                "status": parts[1],
                                "branch": parts[2] if len(parts) > 2 else "",
                            }
                        )

            return runs
        else:
            logger.error(f"Error fetching status: {result.stderr}")
            return []

    except Exception as e:
        logger.error(f"Error fetching workflow status: {e}", exc_info=True)
        return []
