from aura_cli.application.presentation.attention_inbox import (
    AttentionEntry,
    AttentionInbox,
    put_attention,
    resolve_attention,
)


def test_attention_is_correlated_and_replaced_without_duplicates() -> None:
    inbox = AttentionInbox()
    inbox = put_attention(
        inbox, AttentionEntry("approval:1", "task-1", "A", "first", True)
    )
    inbox = put_attention(
        inbox, AttentionEntry("approval:1", "task-1", "A", "updated", True)
    )

    assert len(inbox.entries) == 1
    assert inbox.entries[0].message == "updated"
    assert inbox.blocking_count == 1


def test_resolving_attention_is_idempotent() -> None:
    inbox = put_attention(
        AttentionInbox(), AttentionEntry("approval:1", "task-1", "A", "message", True)
    )

    resolved = resolve_attention(inbox, "approval:1")

    assert resolved.entries == ()
    assert resolve_attention(resolved, "approval:1") == resolved
