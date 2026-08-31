from aura_cli.application.presentation.attention_delivery import (
    AttentionChannel,
    AttentionDeliveryState,
    AttentionPreferences,
    decide_attention_delivery,
    resolve_attention_delivery,
)
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)


def request(intent=PresentationIntent.PROGRESS, **kwargs) -> SurfaceRequest:
    values = {"task_id": "child", "key": "task:child"}
    values.update(kwargs)
    return SurfaceRequest(intent, "Estado mudou", **values)


def test_child_awaiting_user_escalates_outside_current_focus_once() -> None:
    state, delivery = decide_attention_delivery(
        AttentionDeliveryState(),
        request(PresentationIntent.DECISION),
        focused_task_id="parent",
        app_focused=True,
    )
    assert delivery is not None
    assert AttentionChannel.IN_APP in delivery.channels
    assert delivery.terminal_title == "Aura · ação necessária"
    _, duplicate = decide_attention_delivery(
        state,
        request(PresentationIntent.DECISION),
        focused_task_id="parent",
        app_focused=True,
    )
    assert duplicate is None


def test_background_completion_escalates_even_without_task_filter() -> None:
    _, delivery = decide_attention_delivery(
        AttentionDeliveryState(),
        request(tone="success", consolidate=True, background=True),
        focused_task_id=None,
        app_focused=True,
    )
    assert delivery is not None
    assert delivery.terminal_title == "Aura · completed"


def test_resolving_attention_releases_only_that_task_signature() -> None:
    state, delivery = decide_attention_delivery(
        AttentionDeliveryState(),
        request(PresentationIntent.DECISION),
        focused_task_id="parent",
        app_focused=True,
    )
    assert delivery is not None

    other_state, other_delivery = decide_attention_delivery(
        state,
        request(PresentationIntent.ERROR, key="task:other"),
        focused_task_id="parent",
        app_focused=True,
    )
    assert other_delivery is not None

    resolved = resolve_attention_delivery(
        other_state,
        request(
            PresentationIntent.PROGRESS,
            key="task:child",
            resolves_attention=True,
        ),
    )
    assert "task:child:awaiting" not in resolved.signatures
    assert "task:other:failure" in resolved.signatures

    _, repeated = decide_attention_delivery(
        resolved,
        request(PresentationIntent.DECISION),
        focused_task_id="parent",
        app_focused=True,
    )
    assert repeated is not None


def test_preferences_can_disable_completion_and_bell_is_opt_in() -> None:
    _, delivery = decide_attention_delivery(
        AttentionDeliveryState(),
        request(tone="success", consolidate=True, background=True),
        focused_task_id=None,
        app_focused=False,
        preferences=AttentionPreferences(completions=False, audible_bell=True),
    )
    assert delivery is None

    _, failure = decide_attention_delivery(
        AttentionDeliveryState(),
        request(PresentationIntent.ERROR, background=True),
        focused_task_id=None,
        app_focused=False,
        preferences=AttentionPreferences(audible_bell=True),
    )
    assert failure is not None
    assert AttentionChannel.BELL in failure.channels
