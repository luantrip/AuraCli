from types import SimpleNamespace
from unittest.mock import Mock, patch

from aura_cli.application.presentation import (
    ActivityFeed,
    ActivitySection,
    AttentionDeliveryState,
    AttentionInbox,
    AttentionPreferences,
    PresentationIntent,
    SurfaceRequest,
    TuiDrawer,
    TuiSurfaceState,
)
from aura_cli.application.presentation.attention_delivery import (
    AttentionChannel,
    AttentionDelivery,
)
from aura_cli.application.presentation.tui_surfaces import (
    SurfaceDecision,
    SurfaceKind,
)
from aura_cli.tui.app import AuraTUI
import aura_cli.tui.surface_materializer as surface_materializer
from aura_cli.tui.surface_materializer import (
    SurfaceMaterialization,
    prepare_surface,
)


def _app() -> SimpleNamespace:
    return SimpleNamespace(
        activity_feed=ActivityFeed(),
        attention_inbox=AttentionInbox(),
        attention_delivery_state=AttentionDeliveryState(),
        attention_preferences=AttentionPreferences(),
        surface_state=TuiSurfaceState(),
        notify=Mock(),
        _apply_layout_plan=Mock(),
    )


def test_blocking_surface_is_persisted_revealed_and_notified() -> None:
    app = _app()
    request = SurfaceRequest(
        PresentationIntent.DECISION,
        "Executar shell?",
        title="Ação necessária",
        task_id="task-1",
    )

    AuraTUI.present_surface(app, request)
    AuraTUI.present_surface(app, request)

    assert len(app.attention_inbox.entries) == 1
    assert app.attention_inbox.blocking_count == 1
    assert app.surface_state.active_drawer is TuiDrawer.ACTIVITY
    app._apply_layout_plan.assert_called()
    app.notify.assert_called_with(
        "Executar shell?",
        title="Ação necessária",
        severity="warning",
        timeout=10,
    )


def test_activity_surface_marks_the_routed_section() -> None:
    app = _app()

    AuraTUI.present_surface(
        app,
        SurfaceRequest(
            PresentationIntent.PROGRESS,
            "Workflow em execução",
            route="workflow",
            task_id="task-1",
            key="workflow:task-1",
            replace=True,
        ),
    )

    assert app.surface_state.unread[ActivitySection.WORKFLOWS] == 1
    assert app.activity_feed.active[0].content == "Workflow em execução"


def test_tool_surface_uses_central_navigation_registry() -> None:
    app = _app()

    with patch("aura_cli.tui.shell.screen_registry.navigate_route") as navigate:
        AuraTUI.present_surface(
            app,
            SurfaceRequest(
                PresentationIntent.TOOL_OPEN,
                "Abrir arquivos",
                route="files",
            ),
        )

    navigate.assert_called_once_with(app, "files")


def test_surface_pipeline_exposes_prepare_destinations_and_feedback_steps() -> None:
    app = _app()
    request = SurfaceRequest(PresentationIntent.INFORMATION, "Estado")
    materialization = SurfaceMaterialization(
        decision=surface_materializer.decide_surface(request),
        delivery=None,
    )

    with (
        patch.object(
            surface_materializer,
            "prepare_surface",
            return_value=materialization,
        ) as prepare,
        patch.object(surface_materializer, "materialize_destinations") as destinations,
        patch.object(surface_materializer, "deliver_feedback") as feedback,
    ):
        surface_materializer.materialize_surface(app, request)

    prepare.assert_called_once_with(app, request)
    destinations.assert_called_once_with(app, request, materialization)
    feedback.assert_called_once_with(app, materialization)


def test_deliver_feedback_sets_title_bell_and_out_of_focus_notice() -> None:
    app = SimpleNamespace(title="old", bell=Mock(), notify=Mock())
    delivery = AttentionDelivery(
        key="task-1",
        message="Falha em segundo plano",
        channels=(
            AttentionChannel.IN_APP,
            AttentionChannel.TERMINAL_TITLE,
            AttentionChannel.BELL,
        ),
        terminal_title="Aura · falha",
    )
    materialization = SurfaceMaterialization(
        decision=SurfaceDecision(SurfaceKind.ACTIVITY),
        delivery=delivery,
    )

    surface_materializer.deliver_feedback(app, materialization)

    assert app.title == "Aura · falha"
    app.bell.assert_called_once_with()
    app.notify.assert_called_once_with(
        "Falha em segundo plano",
        title="Atividade fora do foco",
        severity="information",
    )


def test_deliver_feedback_does_not_duplicate_notification_primary() -> None:
    app = SimpleNamespace(title="old", notify=Mock())
    delivery = AttentionDelivery(
        key="task-1",
        message="Aviso",
        channels=(AttentionChannel.IN_APP,),
        terminal_title=None,
    )

    surface_materializer.deliver_feedback(
        app,
        SurfaceMaterialization(
            decision=SurfaceDecision(SurfaceKind.NOTIFICATION),
            delivery=delivery,
        ),
    )

    app.notify.assert_not_called()


def test_deliver_feedback_ignores_bell_failure() -> None:
    def failing_bell() -> None:
        raise RuntimeError("bell indisponível")

    app = SimpleNamespace(title="old", bell=failing_bell, notify=Mock())
    delivery = AttentionDelivery(
        key="task-1",
        message="Concluído",
        channels=(AttentionChannel.BELL,),
        terminal_title=None,
    )

    surface_materializer.deliver_feedback(
        app,
        SurfaceMaterialization(
            decision=SurfaceDecision(SurfaceKind.BLOCKING),
            delivery=delivery,
        ),
    )

    app.notify.assert_not_called()


def test_prepare_surface_uses_real_app_focus_signal() -> None:
    app = _app()
    app.is_active = False
    request = SurfaceRequest(PresentationIntent.PROGRESS, "Em segundo plano")

    with patch.object(
        surface_materializer,
        "decide_attention_delivery",
        return_value=(app.attention_delivery_state, None),
    ) as decide_delivery:
        prepare_surface(app, request)

    assert decide_delivery.call_args.kwargs["app_focused"] is False
