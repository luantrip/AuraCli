"""Presentation-neutral decisions and view data for codebase investigations."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

_INVESTIGATION_INDICATORS = (
    "investigate code",
    "investigar codebase",
    "investigar projeto",
    "code analysis",
    "analyze code",
    "analisar projeto",
    "codebase",
    "code structure",
    "code architecture",
    "investigate the code",
    "investigar o projeto",
    "investigar",
)
_OBJECTIVE_PREFIX = re.compile(
    "|".join(
        re.escape(value)
        for value in sorted(_INVESTIGATION_INDICATORS, key=len, reverse=True)
    ),
    flags=re.IGNORECASE,
)


def requests_codebase_investigation(command: str) -> bool:
    """Return whether free-form input explicitly asks for codebase analysis."""
    normalized = command.casefold().strip()
    return any(indicator in normalized for indicator in _INVESTIGATION_INDICATORS)


def codebase_investigation_objective(command: str) -> str:
    """Remove routing phrases while retaining the user's concrete objective."""
    objective = _OBJECTIVE_PREFIX.sub(" ", command)
    objective = " ".join(objective.split()).strip(" ,:;-—")
    return objective or "Full codebase analysis"


@dataclass(frozen=True)
class CodebaseAnalysisView:
    """Framework-independent content consumed by terminal presentation adapters."""

    chat_markdown: str
    panel_summary: str
    issues: tuple[str, ...]
    suggestions: tuple[str, ...]

    def as_panel_payload(self) -> dict[str, Any]:
        return {
            "summary": self.panel_summary,
            "issues": list(self.issues),
            "suggestions": list(self.suggestions),
        }


def build_codebase_analysis_view(results: Mapping[str, Any]) -> CodebaseAnalysisView:
    """Translate analyzer output into stable presentation content."""
    summary = results.get("summary") or {}
    symbols = summary.get("symbols") or {}
    files = int(summary.get("files_processed") or 0)
    lines = int(summary.get("total_lines") or 0)
    classes = int(symbols.get("classes") or 0)
    functions = int(symbols.get("functions") or 0)
    variables = int(symbols.get("variables") or 0)

    suggestions = [
        f"Total de {files} arquivos analisados",
        f"{lines:,} lines of code processed",
    ]
    if classes:
        suggestions.append(f"{classes} classes encontradas")
    if functions:
        suggestions.append(f"{functions} functions found")

    return CodebaseAnalysisView(
        chat_markdown=(
            "# ▥ Codebase Analysis Completed\n\n"
            "**Statistics:**\n"
            f"- Arquivos processados: {files}\n"
            f"- Lines of code: {lines:,}\n"
            f"- Classes: {classes}\n"
            f"- Functions: {functions}\n"
            f"- Variables: {variables}\n\n"
            "**Analysis complete!** See details in the analysis panel (Ctrl+S).\n"
        ),
        panel_summary=(
            "Codebase Analysis\n"
            f"Arquivos: {files} | Linhas: {lines:,}\n"
            f"Classes: {classes} | Functions: {functions}\n"
        ),
        issues=(),
        suggestions=tuple(suggestions),
    )


__all__ = [
    "CodebaseAnalysisView",
    "build_codebase_analysis_view",
    "codebase_investigation_objective",
    "requests_codebase_investigation",
]
