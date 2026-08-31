"""Contracts for codebase-investigation routing and presentation data."""

from aura_cli.application.presentation.codebase_analysis import (
    build_codebase_analysis_view,
    codebase_investigation_objective,
    requests_codebase_investigation,
)


def test_investigation_request_and_objective_are_case_insensitive() -> None:
    command = "ANALISAR CÓDIGO: com foco na fronteira de persistência"
    assert requests_codebase_investigation(command)
    assert (
        codebase_investigation_objective(command)
        == "com foco na fronteira de persistência"
    )


def test_empty_objective_gets_an_explicit_default() -> None:
    assert (
        codebase_investigation_objective("investigar o projeto")
        == "Análise completa do codebase"
    )


def test_view_tolerates_partial_analyzer_output() -> None:
    view = build_codebase_analysis_view(
        {"summary": {"files_processed": 3, "symbols": {"classes": 2}}}
    )
    assert "Arquivos processados: 3" in view.chat_markdown
    assert "2 classes encontradas" in view.suggestions
    assert view.as_panel_payload()["issues"] == []
