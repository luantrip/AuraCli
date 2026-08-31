"""Intelligent refactoring planner — strategic planning before code changes.

Analyses change impact and transitive dependencies, orders changes safely,
estimates risk and execution time, and recommends the best strategy
(incremental / all-at-once / by-dependency). plan_refactoring() is the
main entry point.
"""

from typing import Any, Dict, List

from aura_cli.application.refactoring import (
    RefactoringPlan,
    calculate_overall_risk,
    estimate_refactoring_time,
    parse_occurrences,
    recommend_refactoring_strategy,
)
from aura_cli.core.dependency_analysis import DependencyAnalyzer, get_impact_analysis
from aura_cli.core.logger import get_logger
from aura_cli.core.tools.dev_tools import find_in_files

logger = get_logger(__name__)


def plan_refactoring(
    pattern: str,
    replacement: str,
    scope: str = ".",
    strategy: str = "incremental",
    file_pattern: str = "*.py",
    max_results: int = 1000,
) -> RefactoringPlan:
    """Creates a refactoring plan for a regex pattern replacement across the codebase, without executing it.
    Returns a structured plan with affected files, change count, and risk assessment. Always plan before executing.

    Args:
        pattern: Regex pattern to find (e.g. r'old_function_name').
        replacement: Replacement string.
        scope: Root directory to search (default: current dir).
        strategy: Execution strategy — 'incremental', 'all_at_once', or 'by_dependency'.
        file_pattern: Glob pattern to filter files (default: '*.py').
        max_results: Maximum number of matches to include in the plan.
    """
    logger.info(f"Planejando refatoração: {pattern} -> {replacement}")
    logger.info(f"Estratégia: {strategy}, Escopo: {scope}")

    logger.info("Buscando ocorrências...")
    file_extensions = [".py"] if file_pattern == "*.py" else None
    occurrences_text = find_in_files(pattern, scope, file_extensions, max_results)
    occurrences_list = _parse_occurrences(occurrences_text, max_results)

    logger.info(f"Encontradas {len(occurrences_list)} ocorrências")

    if not occurrences_list:
        logger.warning("Nenhuma ocorrência encontrada")
        plan = RefactoringPlan()
        plan.description = f"Nenhuma ocorrência de '{pattern}' encontrada"
        return plan

    logger.info("Analisando dependências...")
    analyzer = DependencyAnalyzer(scope)
    analyzer.analyze()

    logger.info("Analisando impacto...")
    impact_analysis = {}
    affected_files = set()

    for occ in occurrences_list:
        file_path = occ["file"]
        if file_path not in impact_analysis:
            impact = get_impact_analysis(file_path, "modify", scope)
            impact_analysis[file_path] = impact
            affected_files.add(file_path)
            affected_files.update(impact["affected_files"])

    plan = RefactoringPlan()
    plan.strategy = strategy
    plan.affected_files = sorted(affected_files)
    plan.description = f"Refatoração: '{pattern}' -> '{replacement}' ({len(occurrences_list)} ocorrências)"

    if strategy == "by_dependency":
        logger.info("Ordenando por dependências...")
        plan.steps = _order_by_dependencies(occurrences_list, impact_analysis, analyzer)
    elif strategy == "incremental":
        logger.info("Criando batches incrementais...")
        plan.steps = _create_incremental_batches(occurrences_list, impact_analysis)
    else:
        logger.info("Criando plano sequencial...")
        plan.steps = occurrences_list

    plan.estimated_impact = {
        "total_files": len(affected_files),
        "direct_changes": len(occurrences_list),
        "affected_files": len(affected_files),
        "high_risk_files": len(
            [
                f
                for f, imp in impact_analysis.items()
                if imp["risk_level"] in ["high", "critical"]
            ]
        ),
    }

    plan.risk_level = _calculate_overall_risk(impact_analysis)
    plan.estimated_time = _estimate_time(plan.steps, impact_analysis)

    logger.info(
        f"Plan created: {len(plan.steps)} steps, risk {plan.risk_level}, estimated time: {plan.estimated_time}min"
    )

    return plan


def plan_file_refactoring(
    file_path: str,
    old_content: str,
    new_content: str,
    scope: str = ".",
    strategy: str = "incremental",
) -> RefactoringPlan:
    """Plan a refactoring for a specific file."""
    plan = RefactoringPlan()
    plan.strategy = strategy
    plan.description = f"Refatoração de arquivo: {file_path}"

    impact = get_impact_analysis(file_path, "modify", scope)
    plan.affected_files = impact["affected_files"]
    plan.risk_level = impact["risk_level"]

    plan.add_step(file_path, old_content, new_content, f"Refatorar {file_path}")

    plan.estimated_impact = {
        "total_files": len(impact["affected_files"]),
        "direct_changes": 1,
        "affected_files": len(impact["affected_files"]),
        "high_risk_files": 1 if impact["risk_level"] in ["high", "critical"] else 0,
    }

    plan.estimated_time = _estimate_time(plan.steps, {file_path: impact})

    return plan


def analyze_impact_for_refactoring(
    pattern: str, replacement: str, scope: str = ".", file_pattern: str = "*.py"
) -> Dict[str, Any]:
    """Analyse refactoring impact without building a full plan."""
    logger.info(f"Analisando impacto: {pattern} -> {replacement}")

    file_extensions = [".py"] if file_pattern == "*.py" else None
    occurrences_text = find_in_files(pattern, scope, file_extensions, max_results=1000)
    occurrences_list = _parse_occurrences(occurrences_text, 1000)

    if not occurrences_list:
        return {
            "occurrences": 0,
            "files_affected": 0,
            "risk_level": "low",
            "message": "Nenhuma ocorrência encontrada",
        }

    analyzer = DependencyAnalyzer(scope)
    analyzer.analyze()

    affected_files = set()
    risk_levels = []

    for occ in occurrences_list:
        file_path = occ["file"]
        impact = get_impact_analysis(file_path, "modify", scope)
        affected_files.add(file_path)
        affected_files.update(impact["affected_files"])
        risk_levels.append(impact["risk_level"])

    overall_risk = _calculate_overall_risk_from_levels(risk_levels)

    return {
        "occurrences": len(occurrences_list),
        "files_to_modify": len({occ["file"] for occ in occurrences_list}),
        "files_affected": len(affected_files),
        "risk_level": overall_risk,
        "estimated_time_minutes": len(occurrences_list) * 0.5,
        "recommended_strategy": (
            "incremental" if len(occurrences_list) > 50 else "all_at_once"
        ),
    }


def _parse_occurrences(
    occurrences_text: str, max_results: int = 1000
) -> List[Dict[str, Any]]:
    """Parse find_in_files results into occurrences."""
    return parse_occurrences(occurrences_text, max_results)


def _order_by_dependencies(
    occurrences: List[Dict[str, Any]],
    impact_analysis: Dict[str, Any],
    analyzer: DependencyAnalyzer,
) -> List[Dict[str, Any]]:
    """Sort by dependencies (least-dependent first)."""
    file_weights = {}

    for occ in occurrences:
        file_path = occ["file"]
        if file_path not in file_weights:
            dependents = analyzer.find_dependents(file_path)
            file_weights[file_path] = len(dependents)

    return sorted(
        occurrences, key=lambda x: (file_weights.get(x["file"], 0), x.get("line", 0))
    )


def _create_incremental_batches(
    occurrences: List[Dict[str, Any]], impact_analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Cria batches incrementais ordenados por risco"""
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for occ in occurrences:
        file_path = occ["file"]
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append(occ)

    file_risks = {}
    for file_path, _ in by_file.items():
        impact = impact_analysis.get(file_path, {})
        risk = impact.get("risk_level", "medium")
        risk_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
        file_risks[file_path] = risk_order.get(risk, 1)

    sorted_files = sorted(by_file.keys(), key=lambda f: file_risks.get(f, 1))

    result = []
    for file_path in sorted_files:
        sorted_occs = sorted(by_file[file_path], key=lambda x: x.get("line", 0))
        result.extend(sorted_occs)

    return result


def _calculate_overall_risk(impact_analysis: Dict[str, Any]) -> str:
    """Calculate the overall risk level."""
    if not impact_analysis:
        return "low"

    risk_levels = [imp.get("risk_level", "low") for imp in impact_analysis.values()]
    return _calculate_overall_risk_from_levels(risk_levels)


def _calculate_overall_risk_from_levels(risk_levels: List[str]) -> str:
    """Calculate overall risk from a list of levels."""
    return calculate_overall_risk(risk_levels)


def _estimate_time(steps: List[Dict[str, Any]], impact_analysis: Dict[str, Any]) -> int:
    """Estimate execution time in minutes."""
    return estimate_refactoring_time(steps, impact_analysis)


def suggest_strategy(
    pattern: str, replacement: str, scope: str = ".", file_pattern: str = "*.py"
) -> Dict[str, Any]:
    """Suggest the best strategy for a refactoring."""
    impact = analyze_impact_for_refactoring(pattern, replacement, scope, file_pattern)

    occurrences = impact["occurrences"]
    files_affected = impact["files_affected"]
    risk_level = impact["risk_level"]

    strategy, reason = recommend_refactoring_strategy(
        occurrences=occurrences,
        files_affected=files_affected,
        risk_level=risk_level,
    )
    return {"strategy": strategy, "reason": reason}
