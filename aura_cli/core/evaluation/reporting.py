"""Human- and machine-readable evaluation reports."""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Any

from aura_cli.core.evaluation.metrics import quality_summary
from aura_cli.core.evaluation.models import EvaluationReport


def render_report(report: EvaluationReport, *, title: str = "Aura Evaluation") -> str:
    """Render a compact deterministic Markdown report."""
    summary = quality_summary(report.candidates)
    lines = [
        f"# {title}",
        "",
        f"- Winner: `{report.winner_id or 'none'}`",
        f"- Candidates: {int(summary['count'])}",
        f"- Mean score: {summary['mean']:.3f}",
        f"- Diversity: {report.diversity:.3f}",
        "",
        "| Candidate | Score | Baseline |",
        "|---|---:|:---:|",
    ]
    for candidate in sorted(report.candidates, key=lambda item: item.candidate_id):
        lines.append(f"| `{candidate.candidate_id}` | {candidate.score.weighted(report.criteria_weights):.3f} | {'yes' if candidate.baseline else 'no'} |")
    if report.notes:
        lines.extend(["", "## Notes", "", *[f"- {note}" for note in report.notes]])
    return "\n".join(lines) + "\n"


def save_report(report: EvaluationReport, path: Path, *, title: str = "Aura Evaluation") -> Path:
    """Save both JSON audit data and a readable Markdown report."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"generated_at": time.time(), **report.to_dict()}
    target.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    target.with_suffix(".md").write_text(render_report(report, title=title), encoding="utf-8")
    return target
