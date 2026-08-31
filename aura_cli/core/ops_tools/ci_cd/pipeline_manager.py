"""
CI/CD pipeline manager.

Provides creation and management of complex pipelines
with multiple stages and conditions.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


class StageStatus(Enum):
    """Stage status enum."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PipelineStage:
    """A single stage in a CI/CD pipeline."""

    id: str
    name: str
    commands: List[str]
    dependencies: List[str] = field(default_factory=list)
    condition: Optional[str] = None
    timeout: Optional[int] = None

    status: StageStatus = StageStatus.PENDING
    output: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Pipeline:
    """A complete CI/CD pipeline definition."""

    pipeline_id: str
    name: str
    description: str
    stages: List[PipelineStage] = field(default_factory=list)
    triggers: List[str] = field(default_factory=list)


class PipelineManager:
    """CI/CD pipeline manager."""

    def __init__(self):
        """Initialise the pipeline manager."""
        self.pipelines: Dict[str, Pipeline] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.stats = get_stats()

        logger.info("PipelineManager initialized")

    def create_pipeline(
        self,
        name: str,
        description: str,
        stages: List[Dict[str, Any]],
        triggers: Optional[List[str]] = None,
    ) -> Pipeline:
        """Create a new pipeline definition."""
        pipeline_id = str(uuid.uuid4())[:8]

        pipeline_stages = []
        for stage_data in stages:
            stage = PipelineStage(
                id=stage_data.get("id", str(uuid.uuid4())[:8]),
                name=stage_data["name"],
                commands=stage_data["commands"],
                dependencies=stage_data.get("dependencies", []),
                condition=stage_data.get("condition"),
                timeout=stage_data.get("timeout"),
            )
            pipeline_stages.append(stage)

        pipeline = Pipeline(
            pipeline_id=pipeline_id,
            name=name,
            description=description,
            stages=pipeline_stages,
            triggers=triggers or [],
        )

        self.pipelines[pipeline_id] = pipeline

        logger.info(
            f"Pipeline '{name}' ({pipeline_id}) created with {len(pipeline_stages)} stages"
        )

        return pipeline

    def execute_pipeline(
        self, pipeline_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a pipeline and return its result."""
        from aura_cli.core.ui import display_tool_call
        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        display_tool_call("execute_pipeline", {"pipeline_id": pipeline_id})

        if pipeline_id not in self.pipelines:
            error_msg = f"Pipeline {pipeline_id} not found"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

        pipeline = self.pipelines[pipeline_id]
        context = context or {}

        logger.info(f"Executando pipeline '{pipeline.name}' ({pipeline_id})")

        ordered_stages = self._order_stages(pipeline.stages)

        results = {}
        all_success = True

        for stage in ordered_stages:
            if stage.condition and not self._evaluate_condition(
                stage.condition, context
            ):
                stage.status = StageStatus.SKIPPED
                results[stage.id] = {
                    "status": "skipped",
                    "reason": "condition not met",
                }
                continue
            stage.status = StageStatus.RUNNING
            result = self._execute_stage(stage, context)

            results[stage.id] = result

            if result["success"]:
                stage.status = StageStatus.SUCCESS
            else:
                stage.status = StageStatus.FAILED
                all_success = False
                break

        execution_record = {
            "pipeline_id": pipeline_id,
            "name": pipeline.name,
            "timestamp": datetime.now().isoformat(),
            "success": all_success,
            "stages_results": results,
        }
        self.execution_history.append(execution_record)

        self.stats.track_tool_usage("pipeline_manager")

        if all_success:
            console.print(
                f"[{UIStyles.SUCCESS}]{UIIcons.SUCCESS} "
                f"Pipeline '{pipeline.name}' executed successfully[/{UIStyles.SUCCESS}]"
            )
        else:
            console.print(
                f"[{UIStyles.ERROR}]{UIIcons.ERROR} "
                f"Pipeline '{pipeline.name}' falhou[/{UIStyles.ERROR}]"
            )

        return {
            "pipeline_id": pipeline_id,
            "success": all_success,
            "stages_results": results,
        }

    def _order_stages(self, stages: List[PipelineStage]) -> List[PipelineStage]:
        """Sort stages by dependency order."""
        {s.id: s for s in stages}
        in_degree = {s.id: len(s.dependencies) for s in stages}

        queue = [s for s in stages if in_degree[s.id] == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for stage in stages:
                if current.id in stage.dependencies:
                    in_degree[stage.id] -= 1
                    if in_degree[stage.id] == 0:
                        queue.append(stage)

        remaining = [s for s in stages if s not in result]
        result.extend(remaining)

        return result

    def _execute_stage(
        self, stage: PipelineStage, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single pipeline stage."""
        import subprocess

        from aura_cli.core.logger import get_logger
        from aura_cli.core.tools.shell import _is_safe_command

        logger = get_logger(__name__)
        output_lines = []
        error_lines = []

        for command in stage.commands:
            try:
                cmd = command.format(**context)

                if not _is_safe_command(cmd):
                    reason = "Command contains dangerous patterns or blocked commands"
                    logger.warning(f"Pipeline command blocked: {cmd[:50]}...")
                    return {
                        "success": False,
                        "error": f"Command blocked for security: {reason}",
                        "command": command,
                    }

                try:
                    from aura_cli.core.utils.safe_subprocess import SafeSubprocess

                    executor = SafeSubprocess(timeout_seconds=stage.timeout or 300)
                    result = executor.run_shell(cmd)

                    if result.stdout:
                        output_lines.append(result.stdout)
                    if result.stderr:
                        error_lines.append(result.stderr)

                    if not result.success:
                        return {
                            "success": False,
                            "error": f"Comando falhou com código {result.exit_code}",
                            "output": "\n".join(output_lines),
                            "error_output": "\n".join(error_lines),
                            "command": command,
                        }

                except subprocess.TimeoutExpired:
                    logger.warning(f"Pipeline command timeout: {command[:50]}...")
                    return {
                        "success": False,
                        "error": f"Timeout ao executar comando: {command}",
                        "command": command,
                    }
                except FileNotFoundError as e:
                    logger.error(
                        f"Command not found in pipeline: {command}", exc_info=True
                    )
                    return {
                        "success": False,
                        "error": f"Command not found: {e}",
                        "command": command,
                    }
                except PermissionError as e:
                    logger.error(
                        f"Permission denied in pipeline: {command}", exc_info=True
                    )
                    return {
                        "success": False,
                        "error": f"Permission denied: {e}",
                        "command": command,
                    }
                except OSError as e:
                    logger.error(
                        f"OS error in pipeline command: {command}", exc_info=True
                    )
                    return {
                        "success": False,
                        "error": f"System error: {e}",
                        "command": command,
                    }
            except (KeyError, ValueError) as e:
                logger.error(
                    f"Error formatting command in pipeline: {command}", exc_info=True
                )
                return {
                    "success": False,
                    "error": f"Error formatting command: {e}",
                    "command": command,
                }
            except Exception as e:
                logger.error(
                    f"Unexpected error in pipeline command: {command}", exc_info=True
                )
                return {
                    "success": False,
                    "error": f"Unexpected error: {e}",
                    "command": command,
                }

        return {"success": True, "output": "\n".join(output_lines)}

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """Safely evaluate a stage execution condition."""
        import ast

        try:
            evaluated = condition.format(**context)
            return bool(ast.literal_eval(evaluated))
        except Exception:
            return False

    def get_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Return a pipeline by name."""
        return self.pipelines.get(pipeline_id)

    def list_pipelines(self) -> List[Dict[str, Any]]:
        """Return a list of all pipelines."""
        return [
            {
                "pipeline_id": p.pipeline_id,
                "name": p.name,
                "description": p.description,
                "stages_count": len(p.stages),
                "triggers": p.triggers,
            }
            for p in self.pipelines.values()
        ]

    def get_execution_history(
        self, pipeline_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return the pipeline execution history."""
        if pipeline_id:
            return [
                e for e in self.execution_history if e["pipeline_id"] == pipeline_id
            ]
        return self.execution_history.copy()
