"""Pure contracts and decision policies for refactoring plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional


@dataclass
class RefactoringPlan:
    """Structured, infrastructure-neutral refactoring plan."""

    steps: list[dict[str, Any]] = field(default_factory=list)
    estimated_impact: dict[str, Any] = field(default_factory=dict)
    risk_level: str = "low"
    rollback_points: list[str] = field(default_factory=list)
    strategy: str = "incremental"
    estimated_time: int = 0
    affected_files: list[str] = field(default_factory=list)
    description: str = ""

    def add_step(
        self,
        file_path: str,
        old_content: str,
        new_content: str,
        description: str = "",
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.steps.append(
            {
                "file": file_path,
                "before": old_content,
                "after": new_content,
                "description": description,
                "metadata": metadata or {},
            }
        )

    def get_batches(self, batch_size: int = 10) -> list[list[dict[str, Any]]]:
        if batch_size <= 0:
            raise ValueError("Refactoring batch size must be positive")
        return [
            self.steps[index : index + batch_size]
            for index in range(0, len(self.steps), batch_size)
        ]


def parse_occurrences(text: str, max_results: int = 1000) -> list[dict[str, Any]]:
    """Parse unique ``path:line:content`` search records."""
    if max_results <= 0:
        return []
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for line in text.splitlines():
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        file_path = parts[0].strip()
        try:
            line_number = int(parts[1].strip())
        except ValueError:
            continue
        key = (file_path, line_number)
        if not file_path or key in seen:
            continue
        seen.add(key)
        results.append(
            {"file": file_path, "line": line_number, "content": parts[2].strip()}
        )
        if len(results) >= max_results:
            break
    return results


def calculate_overall_risk(risk_levels: Iterable[str]) -> str:
    """Collapse individual risk levels to their highest severity."""
    ranks = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    normalized = [level if level in ranks else "low" for level in risk_levels]
    return max(normalized, key=ranks.__getitem__, default="low")


def estimate_refactoring_time(
    steps: Iterable[Mapping[str, Any]],
    impact_analysis: Mapping[str, Mapping[str, Any]],
) -> int:
    """Estimate whole minutes from files, high-risk impact and step count."""
    items = list(steps)
    if not items:
        return 0
    unique_files = len({str(step.get("file", "")) for step in items})
    high_risk = sum(
        1
        for impact in impact_analysis.values()
        if impact.get("risk_level") in {"high", "critical"}
    )
    return max(1, int(unique_files + high_risk * 0.5 + len(items) * 0.1))


def recommend_refactoring_strategy(
    *, occurrences: int, files_affected: int, risk_level: str
) -> tuple[str, str]:
    """Recommend an execution strategy and human-readable rationale."""
    if occurrences == 0:
        return "none", "Nenhuma ocorrência encontrada"
    if occurrences < 10 and files_affected < 5:
        return (
            "all_at_once",
            f"Poucas mudanças ({occurrences} ocorrências, {files_affected} arquivos)",
        )
    if risk_level in {"high", "critical"}:
        return (
            "by_dependency",
            f"Alto risco ({risk_level}), ordenar por dependências é mais seguro",
        )
    if occurrences > 100:
        return (
            "incremental",
            f"Muitas mudanças ({occurrences} ocorrências), execução incremental recomendada",
        )
    return "incremental", "Estratégia padrão segura para mudanças médias"
