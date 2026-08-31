"""Use case for consolidating scratchpad rules into a constitution."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import re
from typing import Protocol


class NotebookPort(Protocol):
    def read_page(self, category: str, page_name: str) -> str | None: ...
    def list_pages(self, category: str) -> Sequence[str]: ...
    def write_page(self, category: str, page_name: str, content: str) -> bool: ...


@dataclass(frozen=True)
class ConsolidatedRule:
    category: str
    content: str


class ConsolidationStatus(Enum):
    CONSOLIDATED = "consolidated"
    NO_CONSTITUTION = "no_constitution"
    NO_PENDING_PAGES = "no_pending_pages"
    NO_RULES = "no_rules"
    SAVE_FAILED = "save_failed"


@dataclass(frozen=True)
class ConsolidationOutcome:
    status: ConsolidationStatus
    page_count: int = 0
    rule_count: int = 0
    updated_constitution: str | None = None


def extract_consolidated_rules(
    notebook: NotebookPort,
    pages: Sequence[str],
) -> list[ConsolidatedRule]:
    """Parse categorized non-heading lines from scratchpad pages."""
    rules: list[ConsolidatedRule] = []
    for page_name in pages:
        content = notebook.read_page("scratchpad", page_name)
        if not content:
            continue
        sections = re.findall(r"##\s+(.+?)\n+(.+?)(?=\n##|\Z)", content, re.DOTALL)
        for category, section in sections:
            for line in section.splitlines():
                candidate = line.strip()
                if not candidate or candidate.startswith("#"):
                    continue
                candidate = re.sub(r"^(?:[-*+]|\d+[.)])\s+", "", candidate)
                if candidate:
                    rules.append(ConsolidatedRule(category.strip(), candidate))
    return rules


def build_consolidation_section(
    rules: Sequence[ConsolidatedRule],
    *,
    timestamp: datetime,
) -> str:
    """Build the constitution appendix in deterministic category order."""
    grouped: dict[str, list[str]] = defaultdict(list)
    for rule in rules:
        grouped[rule.category or "Regra Geral"].append(rule.content)

    parts = [
        "\n\n---\n\n## Regras Aprendidas e Consolidadas\n\n",
        f"*Consolidação manual: {timestamp:%Y-%m-%d %H:%M:%S}*\n\n",
    ]
    for category, contents in grouped.items():
        parts.append(f"### {category}\n\n")
        parts.extend(f"- {content}\n\n" for content in contents)
    return "".join(parts)


def consolidate_notebook_rules(
    notebook: NotebookPort,
    *,
    clock: Callable[[], datetime] = datetime.now,
) -> ConsolidationOutcome:
    """Consolidate every pending rule page and return a UI-neutral outcome."""
    constitution = notebook.read_page("notebook", "constitution.md")
    if not constitution:
        return ConsolidationOutcome(ConsolidationStatus.NO_CONSTITUTION)

    pages = [
        page
        for page in notebook.list_pages("scratchpad")
        if "consolidacao_regras" in page.casefold()
    ]
    if not pages:
        return ConsolidationOutcome(ConsolidationStatus.NO_PENDING_PAGES)

    rules = extract_consolidated_rules(notebook, pages)
    if not rules:
        return ConsolidationOutcome(ConsolidationStatus.NO_RULES, page_count=len(pages))

    updated = constitution + build_consolidation_section(rules, timestamp=clock())
    saved = notebook.write_page("notebook", "constitution.md", updated)
    return ConsolidationOutcome(
        ConsolidationStatus.CONSOLIDATED if saved else ConsolidationStatus.SAVE_FAILED,
        page_count=len(pages),
        rule_count=len(rules),
        updated_constitution=updated if saved else None,
    )


__all__ = [
    "ConsolidatedRule",
    "ConsolidationOutcome",
    "ConsolidationStatus",
    "NotebookPort",
    "build_consolidation_section",
    "consolidate_notebook_rules",
    "extract_consolidated_rules",
]
