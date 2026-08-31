"""Use-case tests for scratchpad rule consolidation."""

from datetime import datetime

from aura_cli.application.workspace.consolidation import (
    ConsolidationStatus,
    consolidate_notebook_rules,
)


class NotebookStub:
    def __init__(self) -> None:
        self.pages = {
            ("notebook", "constitution.md"): "# Constituição",
            ("scratchpad", "consolidacao_regras_1.md"): (
                "## Python\n\n- Prefira pathlib\n2. Evite estado global\n\n"
                "## Testes\n\n* Isole artefatos\n"
            ),
        }
        self.saved: tuple[str, str, str] | None = None

    def read_page(self, category: str, page_name: str) -> str | None:
        return self.pages.get((category, page_name))

    def list_pages(self, category: str) -> list[str]:
        return [name for page_category, name in self.pages if page_category == category]

    def write_page(self, category: str, page_name: str, content: str) -> bool:
        self.saved = (category, page_name, content)
        return True


def test_consolidates_rules_with_injected_timestamp() -> None:
    notebook = NotebookStub()
    outcome = consolidate_notebook_rules(
        notebook,
        clock=lambda: datetime(2026, 8, 11, 12, 30, 45),
    )

    assert outcome.status is ConsolidationStatus.CONSOLIDATED
    assert outcome.page_count == 1
    assert outcome.rule_count == 3
    assert "2026-08-11 12:30:45" in (outcome.updated_constitution or "")
    assert "### Python" in (outcome.updated_constitution or "")
    assert "- Prefira pathlib" in (outcome.updated_constitution or "")
    assert "- - Prefira pathlib" not in (outcome.updated_constitution or "")
    assert notebook.saved is not None


def test_missing_constitution_does_not_write() -> None:
    notebook = NotebookStub()
    notebook.pages.pop(("notebook", "constitution.md"))

    outcome = consolidate_notebook_rules(notebook)

    assert outcome.status is ConsolidationStatus.NO_CONSTITUTION
    assert notebook.saved is None


def test_empty_pending_page_reports_no_rules() -> None:
    notebook = NotebookStub()
    notebook.pages[("scratchpad", "consolidacao_regras_1.md")] = "# sem seções"

    outcome = consolidate_notebook_rules(notebook)

    assert outcome.status is ConsolidationStatus.NO_RULES
    assert outcome.page_count == 1
