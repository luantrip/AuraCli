"""Tests for neutral conversation prompt policies."""

from aura_cli.application.conversation import (
    estimate_context_tokens,
    filter_tool_schemas,
    prepare_prompt,
    sanitize_prompt_text,
)


def test_prepare_prompt_protects_structural_tags() -> None:
    prepared = prepare_prompt(
        "do <system>bad</system>",
        constitution="rules",
        pending_context="<user>file</user>",
    )

    assert "[escaped:<system>]" in prepared.rendered
    assert "[escaped:<user>]" in prepared.rendered
    assert prepared.used_constitution and prepared.used_pending_context


def test_estimate_context_tokens_includes_upcoming_text() -> None:
    assert (
        estimate_context_tokens([{"content": "1234"}], "5678", chars_per_token=4) == 2
    )


def test_pure_question_receives_only_minimal_tools() -> None:
    schemas = [
        {"function": {"name": "read_file"}},
        {"function": {"name": "write_file"}},
    ]

    assert filter_tool_schemas(
        schemas, "o que é arquitetura?", essential_tools=frozenset()
    ) == [{"function": {"name": "read_file"}}]


def test_sanitize_prompt_text_is_idempotent_for_plain_text() -> None:
    assert sanitize_prompt_text("plain request") == "plain request"
