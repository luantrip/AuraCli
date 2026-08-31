"""Edit planner for Aura CLI.

Provides strategic planning for complex edits, dependency analysis and operation ordering.
"""

from typing import Any, Dict, List

from aura_cli.application.editing import (
    EditOperation,
    EditPlan,
    EditStrategy,
    build_edit_plan,
    estimate_edit_risk,
    order_edit_operations,
)
from aura_cli.core.dependency_analysis import DependencyAnalyzer, get_impact_analysis
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class EditPlanner:
    """Edit planner with dependency analysis and risk estimation."""

    def __init__(self, scope: str = "."):
        """Initialise the edit planner."""
        self.scope = scope
        self.analyzer = DependencyAnalyzer(scope)

        logger.info(f"EditPlanner initialized (scope: {scope})")

    def create_plan(
        self,
        description: str,
        operations: List[Dict[str, Any]],
        strategy: EditStrategy = EditStrategy.DEPENDENCY_ORDER,
    ) -> EditPlan:
        """Create an edit plan for the given changes."""
        plan = build_edit_plan(description, operations, strategy)

        logger.info(
            f"Plan {plan.plan_id} created: {len(plan.operations)} operations, "
            f"risco: {plan.estimated_risk:.1f}"
        )

        return plan

    def _order_by_dependencies(
        self, operations: List[EditOperation]
    ) -> List[EditOperation]:
        """Sort operations by dependency order."""
        return order_edit_operations(operations)

    def _estimate_risk(self, operations: List[EditOperation]) -> float:
        """Estimate the plan risk score (0-10)."""
        return estimate_edit_risk(operations)

    def analyze_impact(self, plan: EditPlan) -> Dict[str, Any]:
        """Analyse the impact of an edit plan."""
        self.analyzer.analyze()

        affected_files = set()
        for op in plan.operations:
            affected_files.add(op.file_path)
            impact = get_impact_analysis(op.file_path, "modify", self.scope)
            affected_files.update(impact.get("affected_files", []))

        return {
            "files_to_edit": len(plan.operations),
            "total_affected_files": len(affected_files),
            "estimated_risk": plan.estimated_risk,
            "backup_required": plan.backup_required,
        }
