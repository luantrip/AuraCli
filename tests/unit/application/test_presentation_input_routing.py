"""Priority and availability contracts for free-form presentation input."""

from unittest.mock import Mock

from aura_cli.application.presentation.input_routing import (
    PresentationInputRoute,
    route_presentation_input,
)


def test_runtime_availability_precedes_all_execution_routes() -> None:
    router = Mock()

    assert (
        route_presentation_input(
            "investigue o codebase", router=router, runtime_available=False
        )
        is PresentationInputRoute.UNAVAILABLE
    )
    router.should_use_agi_worker.assert_not_called()


def test_codebase_investigation_has_priority_over_agi_heuristic() -> None:
    router = Mock()
    router.should_use_agi_worker.return_value = True

    route = route_presentation_input(
        "investigue o codebase e implemente melhorias",
        router=router,
        runtime_available=True,
    )

    assert route is PresentationInputRoute.CODEBASE_INVESTIGATION
    router.should_use_agi_worker.assert_not_called()


def test_agi_and_direct_routes_are_mutually_exclusive() -> None:
    router = Mock()
    router.should_use_agi_worker.side_effect = [True, False]

    assert (
        route_presentation_input(
            "implemente a API", router=router, runtime_available=True
        )
        is PresentationInputRoute.AGI_WORKER
    )
    assert (
        route_presentation_input(
            "explique a API", router=router, runtime_available=True
        )
        is PresentationInputRoute.DIRECT
    )
