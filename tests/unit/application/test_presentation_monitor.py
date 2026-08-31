"""Framework-neutral content monitor projections."""

from types import SimpleNamespace

from aura_cli.application.presentation.monitor import (
    MonitorContentMode,
    build_address_view,
    build_content_view,
    build_health_view,
    build_tab_views,
    normalize_monitor_url,
)


def tab(title: str = "", *, loading: bool = False):
    return SimpleNamespace(
        title=title,
        url="https://example.test",
        loading=loading,
        can_go_back=lambda: True,
        can_go_forward=lambda: False,
    )


def test_normalizes_remote_local_and_special_addresses() -> None:
    assert normalize_monitor_url("example.com") == "https://example.com"
    assert normalize_monitor_url("/tmp/page.html") == "file:///tmp/page.html"
    assert normalize_monitor_url(" about:blank ") == "about:blank"


def test_content_precedence_and_types_are_explicit() -> None:
    assert build_content_view("{}", "application/json").mode is MonitorContentMode.JSON
    assert (
        build_content_view("# Hi", "text/markdown").mode is MonitorContentMode.MARKDOWN
    )
    assert build_content_view("", error="boom").content == "✗ boom"
    assert build_content_view("old", loading=True).mode is MonitorContentMode.LOADING


def test_address_tabs_and_health_are_bounded_views() -> None:
    address = build_address_view(tab("Example"))
    tabs = build_tab_views([tab("A very long browser tab title", loading=True)], 0)

    assert address.secure and address.can_back and not address.can_forward
    assert tabs[0].active and tabs[0].label == "● A very long ..."
    assert (
        build_health_view(SimpleNamespace(is_error=False, text="a\nb\nc\nd")).preview
        == "a\nb\nc"
    )
    assert (
        build_health_view(SimpleNamespace(is_error=True, error="offline")).status
        == "error"
    )
