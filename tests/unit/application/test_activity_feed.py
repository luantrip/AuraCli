from aura_cli.application.presentation.activity_feed import (
    ActivityFeed,
    reduce_activity,
)
from aura_cli.application.presentation.tui_surfaces import (
    PresentationIntent,
    SurfaceRequest,
)


def request(content: str, *, final: bool = False) -> SurfaceRequest:
    return SurfaceRequest(
        PresentationIntent.PROGRESS,
        content,
        key="task:1",
        replace=not final,
        consolidate=final,
    )


def test_live_updates_replace_same_correlated_row() -> None:
    feed = reduce_activity(ActivityFeed(), request("running 1s"))
    feed = reduce_activity(feed, request("running 2s"))

    assert [item.content for item in feed.active] == ["running 2s"]
    assert feed.completed == ()


def test_terminal_update_removes_live_row_and_consolidates_once() -> None:
    feed = reduce_activity(ActivityFeed(), request("running"))
    feed = reduce_activity(feed, request("completed", final=True))
    feed = reduce_activity(feed, request("completed", final=True))

    assert feed.active == ()
    assert [item.content for item in feed.completed] == ["completed"]


def test_unkeyed_live_updates_receive_a_stable_correlation_key() -> None:
    first = SurfaceRequest(
        PresentationIntent.PROGRESS,
        "running 1s",
        task_id="task-implicit",
        replace=True,
    )
    second = SurfaceRequest(
        PresentationIntent.PROGRESS,
        "running 2s",
        task_id="task-implicit",
        replace=True,
    )

    feed = reduce_activity(ActivityFeed(), first)
    feed = reduce_activity(feed, second)

    assert len(feed.active) == 1
    assert feed.active[0].content == "running 2s"
    assert feed.active[0].key == "implicit:task-implicit:progress:activity:untitled"
