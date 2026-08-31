import pytest

from aura_cli.application.presentation.tool_grammar import (
    ToolFamily,
    describe_tool_activity,
    safe_preview,
)


@pytest.mark.parametrize(
    ("name", "args", "family", "label"),
    [
        ("read_file", {"path": "src/app.py"}, ToolFamily.READ, "Ler src/app.py"),
        (
            "advanced_grep_search",
            {"pattern": "TODO", "path": "src"},
            ToolFamily.SEARCH,
            "Buscar “TODO” em src",
        ),
        ("edit_file", {"file_path": "a.py"}, ToolFamily.EDIT, "Editar a.py"),
        (
            "run_shell_command",
            {"command": "python app.py"},
            ToolFamily.SHELL,
            "Executar python app.py",
        ),
        ("git_status", {}, ToolFamily.GIT, "Git"),
        (
            "run_shell_command",
            {"command": "pytest -q"},
            ToolFamily.TEST,
            "Testar pytest -q",
        ),
        (
            "mcp_call",
            {"server": "github", "operation": "issues.list"},
            ToolFamily.MCP,
            "Consultar issues.list",
        ),
    ],
)
def test_tool_family_has_specific_compact_grammar(name, args, family, label) -> None:
    grammar = describe_tool_activity(name, args)
    assert grammar.family is family
    assert grammar.label == label


def test_outcome_uses_family_specific_evidence_counts() -> None:
    search = describe_tool_activity(
        "grep", {"pattern": "x"}, result={"matches": 8, "files": 3}
    )
    tests = describe_tool_activity("pytest", {}, result={"passed": 12, "failed": 1})
    assert search.outcome == "matches=8 · files=3"
    assert tests.outcome == "passed=12 · failed=1"


def test_safe_preview_masks_common_credential_values() -> None:
    command = "curl -H 'Authorization: Bearer super-secret-token' token=abc123"

    preview = safe_preview(command, key="command")

    assert preview is not None
    assert "super-secret-token" not in preview
    assert "abc123" not in preview
    assert "[oculto]" in preview


def test_safe_preview_masks_explicitly_sensitive_fields() -> None:
    assert safe_preview("secret-value", key="api_key") == "[oculto]"
    assert safe_preview("password-value", key="password") == "[oculto]"


def test_long_shell_command_is_bounded() -> None:
    grammar = describe_tool_activity("run_shell_command", {"command": "x" * 100})
    assert grammar.target is not None
    assert len(grammar.target) == 72
    assert grammar.target.endswith("…")
