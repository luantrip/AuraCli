"""Tests for core/memory/constitution_template.py — pure functions, no I/O."""

import re

from aura_cli.core.memory.constitution_template import (
    CONSTITUTION_QUESTIONS,
    CONSTITUTION_TEMPLATE,
    MINIMAL_CONSTITUTION_TEMPLATE,
    ConstitutionSection,
    generate_constitution,
    get_constitution_summary,
    validate_constitution,
)


class TestConstitutionSection:
    def test_defaults(self):
        s = ConstitutionSection(title="Test", content="body")
        assert s.title == "Test"
        assert s.content == "body"
        assert s.required is False
        assert s.examples == []

    def test_required_with_examples(self):
        s = ConstitutionSection(title="T", content="c", required=True, examples=["ex1"])
        assert s.required is True
        assert s.examples == ["ex1"]


class TestGenerateConstitution:
    def test_minimal_template_defaults(self):
        result = generate_constitution({})
        assert "Constituição do Projeto" in result
        assert "Python" in result  # default language
        assert "SQLite" in result  # default database
        assert "REST" in result  # default api_style
        assert "snake_case" in result

    def test_minimal_template_custom_answers(self):
        answers = {
            "language": "Go",
            "database": "PostgreSQL",
            "api_style": "gRPC",
            "naming_convention": "camelCase",
        }
        result = generate_constitution(answers, template="minimal")
        assert "Go" in result
        assert "PostgreSQL" in result
        assert "gRPC" in result
        assert "camelCase" in result

    def test_full_template(self):
        answers = {
            "project_description": "API REST para gerenciar tarefas",
            "language": "Python",
            "frameworks": "FastAPI",
            "database": "PostgreSQL",
            "naming_convention": "snake_case",
        }
        result = generate_constitution(answers, template="full")
        assert "FastAPI" in result
        assert "PostgreSQL" in result
        assert "PascalCase" in result  # class naming hardcoded
        assert "UPPER_SNAKE_CASE" in result  # const naming hardcoded

    def test_full_template_contains_date(self):
        result = generate_constitution({}, template="full")
        # Should contain a date like 2026-06-08
        assert re.search(r"\d{4}-\d{2}-\d{2}", result)

    def test_minimal_is_default(self):
        result_default = generate_constitution({})
        result_minimal = generate_constitution({}, template="minimal")
        assert result_default == result_minimal

    def test_full_template_all_defaults(self):
        result = generate_constitution({}, template="full")
        assert "Constituição do Projeto" in result
        assert "pytest" in result  # default test tool
        assert "Conventional Commits" in result


class TestGetConstitutionSummary:
    def test_empty_constitution(self):
        summary = get_constitution_summary("")
        assert summary["has_stack"] is False
        assert summary["has_conventions"] is False
        assert summary["sections"] == []

    def test_detects_stack(self):
        summary = get_constitution_summary("## Stack Tecnológico\n- Python")
        assert summary["has_stack"] is True
        assert "stack" in summary["sections"]

    def test_detects_stack_via_linguagem(self):
        summary = get_constitution_summary("Linguagem: Python")
        assert summary["has_stack"] is True

    def test_detects_conventions(self):
        summary = get_constitution_summary("## Convenções de código\nsnake_case")
        assert summary["has_conventions"] is True
        assert "conventions" in summary["sections"]

    def test_detects_conventions_via_nomenclatura(self):
        summary = get_constitution_summary("Nomenclatura: snake_case")
        assert summary["has_conventions"] is True

    def test_detects_tests(self):
        summary = get_constitution_summary("## Testes\npytest")
        assert summary["has_tests"] is True
        assert "tests" in summary["sections"]

    def test_detects_tests_case_insensitive(self):
        summary = get_constitution_summary("test strategy: unit tests")
        assert summary["has_tests"] is True

    def test_detects_git(self):
        summary = get_constitution_summary("## Git\nConventional Commits")
        assert summary["has_git"] is True
        assert "git" in summary["sections"]

    def test_detects_commit(self):
        summary = get_constitution_summary("Commit format: feature/*")
        assert summary["has_git"] is True

    def test_detects_security(self):
        summary = get_constitution_summary("## Segurança\nNão expor secrets")
        assert summary["has_security"] is True
        assert "security" in summary["sections"]

    def test_detects_security_english(self):
        summary = get_constitution_summary("Security practices: validate inputs")
        assert summary["has_security"] is True

    def test_learned_rules_count(self):
        constitution = "## Regras Aprendidas\n- Regra 1\n- Regra 2\n- Regra 3"
        summary = get_constitution_summary(constitution)
        assert summary["learned_rules_count"] == 3

    def test_learned_rules_none(self):
        constitution = "## Stack\nPython"
        summary = get_constitution_summary(constitution)
        assert summary["learned_rules_count"] == 0

    def test_full_constitution(self):
        result = generate_constitution(
            {"language": "Python", "frameworks": "FastAPI"}, template="full"
        )
        summary = get_constitution_summary(result)
        assert summary["has_stack"] is True
        assert summary["has_conventions"] is True
        assert summary["has_tests"] is True
        assert summary["has_git"] is True
        assert summary["has_security"] is True


class TestValidateConstitution:
    def test_empty_returns_issue(self):
        issues = validate_constitution("")
        assert any("short or empty" in i for i in issues)

    def test_too_short_returns_issue(self):
        issues = validate_constitution("short text")
        assert any("short or empty" in i for i in issues)

    def test_valid_minimal_constitution(self):
        result = generate_constitution(
            {"language": "Python", "naming_convention": "snake_case"},
            template="minimal",
        )
        issues = validate_constitution(result)
        # "Convenções" is present, "Linguagem" is present via language field
        assert isinstance(issues, list)

    def test_full_constitution_no_critical_issues(self):
        result = generate_constitution({}, template="full")
        issues = validate_constitution(result)
        # Full template should have no "Missing recommended section" for Stack/Convenções
        missing = [i for i in issues if "Missing recommended section" in i]
        # stack and conventions should be found
        assert not any("Stack" in i for i in missing)

    def test_returns_list(self):
        issues = validate_constitution("x" * 200)
        assert isinstance(issues, list)

    def test_missing_sections_flagged(self):
        # Constitution without stack/convention/language keywords
        issues = validate_constitution("Hello world " * 20)
        assert len(issues) > 0


class TestConstants:
    def test_template_has_placeholders(self):
        assert "{project_description}" in CONSTITUTION_TEMPLATE
        assert "{created_date}" in CONSTITUTION_TEMPLATE

    def test_minimal_template_has_placeholders(self):
        assert "{language}" in MINIMAL_CONSTITUTION_TEMPLATE
        assert "{database}" in MINIMAL_CONSTITUTION_TEMPLATE

    def test_questions_structure(self):
        assert len(CONSTITUTION_QUESTIONS) > 0
        for q in CONSTITUTION_QUESTIONS:
            assert "id" in q
            assert "question" in q
            assert "default" in q
