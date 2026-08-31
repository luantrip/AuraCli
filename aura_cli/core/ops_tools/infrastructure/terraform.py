"""
Terraform manager for Aura CLI infrastructure operations.

Provides Terraform infrastructure operations for infrastructure as code.
"""

from dataclasses import dataclass, field
import json
import subprocess
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Tuple,
)

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


@dataclass
class TerraformPlan:
    """Terraform plan (plan_id, changes, to_add, to_destroy, to_modify)."""

    plan_id: str
    changes: Dict[str, Any] = field(default_factory=dict)
    to_add: int = 0
    to_change: int = 0
    to_destroy: int = 0


@dataclass
class TerraformState:
    """Terraform state snapshot (resources, outputs, version)."""

    resources: List[Dict[str, Any]] = field(default_factory=list)
    outputs: Dict[str, Any] = field(default_factory=dict)
    version: int = 0


class TerraformManager:
    """Manages Terraform operations: init, plan, apply, destroy."""

    def __init__(self):
        """Initialise the Terraform manager."""
        self.stats = get_stats()

        import shutil

        self.terraform_available = shutil.which("terraform") is not None

        if not self.terraform_available:
            logger.warning("Terraform not found. Functionality limited.")
        else:
            logger.info("TerraformManager initialized")

    def _run_terraform(
        self, command: List[str], working_dir: str = ".", timeout: int = 300
    ) -> Tuple[bool, str]:
        """Run a terraform command and return the output."""
        if not self.terraform_available:
            return False, "Terraform não disponível"

        try:
            result = subprocess.run(
                ["terraform", *command],
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return result.returncode == 0, (
                result.stdout if result.returncode == 0 else result.stderr
            )

        except subprocess.TimeoutExpired:
            return False, "Timeout ao executar comando"
        except Exception as e:
            return False, str(e)

    def init(self, working_dir: str = ".") -> str:
        """Initialise a Terraform project."""
        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        display_tool_call("terraform_init", {"working_dir": working_dir})

        success, output = self._run_terraform(["init"], working_dir, timeout=300)

        if success:
            logger.info(f"Terraform initialized in {working_dir}")
            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Terraform initialized[/{UIStyles.SUCCESS}]"
            )
            self.stats.track_tool_usage("terraform_init")
            return "Terraform initialized successfully"
        else:
            error_msg = f"Error initializing Terraform: {output}"
            logger.error(error_msg)
            return error_msg

    def plan(self, working_dir: str = ".") -> Optional[TerraformPlan]:
        """Create a Terraform plan."""
        from aura_cli.core.ui import display_tool_call

        display_tool_call("terraform_plan", {"working_dir": working_dir})

        success, output = self._run_terraform(
            ["plan", "-out=tfplan", "-json"], working_dir
        )

        if not success:
            logger.error(f"Error creating plan: {output}")
            return None

        import uuid

        plan = TerraformPlan(plan_id=str(uuid.uuid4())[:8])

        lines = output.split("\n")
        for line in lines:
            if "to add" in line.lower():
                plan.to_add += 1
            elif "to change" in line.lower():
                plan.to_change += 1
            elif "to destroy" in line.lower():
                plan.to_destroy += 1

        logger.info(
            f"Plan created: +{plan.to_add} ~{plan.to_change} -{plan.to_destroy}"
        )

        return plan

    def apply(self, working_dir: str = ".", auto_approve: bool = False) -> str:
        """Apply Terraform changes."""
        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        display_tool_call(
            "terraform_apply",
            {"working_dir": working_dir, "auto_approve": auto_approve},
        )

        cmd = ["apply"]
        if auto_approve:
            cmd.append("-auto-approve")
        else:
            cmd.append("tfplan")

        success, output = self._run_terraform(cmd, working_dir, timeout=600)

        if success:
            logger.info("Terraform apply executed successfully")
            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Terraform apply completed[/{UIStyles.SUCCESS}]"
            )
            self.stats.track_tool_usage("terraform_apply")
            return "Apply completed successfully"
        else:
            error_msg = f"Erro no apply: {output}"
            logger.error(error_msg)
            return error_msg

    def get_state(self, working_dir: str = ".") -> Optional[TerraformState]:
        """Get the current Terraform state."""
        success, output = self._run_terraform(["show", "-json"], working_dir)

        if not success:
            return None

        try:
            data = json.loads(output)

            state = TerraformState(version=data.get("format_version", 0))

            return state

        except Exception as e:
            logger.error(f"Error processing state: {e}", exc_info=True)
            return None
