from types import SimpleNamespace
from unittest.mock import Mock

from aura_cli.application.sessions import (
    LoadSessionStatus,
    count_conversation_messages,
    load_session_into_workspace,
    save_workspace_session,
)


def _session(session_id: str, name: str, *, model: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        id=session_id,
        name=name,
        conversation_history=[{"role": "user", "content": "hello"}],
        model=model,
    )


def test_save_workspace_session_captures_history_and_model() -> None:
    repository = Mock()
    session = _session("abc123", "work")
    repository.create_session.return_value = session
    history = [
        {"role": "system", "content": "rules"},
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi"},
    ]

    outcome = save_workspace_session(
        repository,
        name="work",
        conversation_history=history,
        model="gpt-test",
    )

    assert outcome.session_id == "abc123"
    assert outcome.message_count == 2
    assert session.conversation_history == history
    assert session.model == "gpt-test"
    repository.save_session.assert_called_once_with(session)


def test_load_resolves_unique_prefix_and_restores_workspace() -> None:
    repository = Mock()
    session = _session("abcdef12", "saved", model="gpt-test")
    repository.load_session.side_effect = [None, session]
    repository.list_sessions.return_value = [session]
    workspace = SimpleNamespace(conversation_history=[], final_model="old")

    outcome = load_session_into_workspace(
        repository, reference="abc", workspace=workspace
    )

    assert outcome.status is LoadSessionStatus.LOADED
    assert outcome.message_count == 1
    assert workspace.conversation_history == session.conversation_history
    assert workspace.final_model == "gpt-test"
    assert repository.load_session.call_args_list[1].args == ("abcdef12",)


def test_load_reports_ambiguity_without_mutating_workspace() -> None:
    repository = Mock()
    repository.load_session.return_value = None
    repository.list_sessions.return_value = [
        _session("abc111", "one"),
        _session("abc222", "two"),
    ]
    workspace = SimpleNamespace(conversation_history=[], final_model="old")

    outcome = load_session_into_workspace(
        repository, reference="abc", workspace=workspace
    )

    assert outcome.status is LoadSessionStatus.AMBIGUOUS
    assert len(outcome.matches) == 2
    assert workspace.conversation_history == []


def test_load_reports_missing_session() -> None:
    repository = Mock()
    repository.load_session.return_value = None
    repository.list_sessions.return_value = []

    outcome = load_session_into_workspace(
        repository,
        reference="missing",
        workspace=SimpleNamespace(conversation_history=[], final_model="old"),
    )

    assert outcome.status is LoadSessionStatus.NOT_FOUND


def test_conversation_count_excludes_non_conversation_roles() -> None:
    assert (
        count_conversation_messages(
            [{"role": "tool"}, {"role": "user"}, {"role": "assistant"}]
        )
        == 2
    )
