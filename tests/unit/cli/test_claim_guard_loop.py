import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from aura_cli.application.execution import TurnExecution
from aura_cli.cli import function_call_handler as handler


def _response(content: str):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=[]))
        ]
    )


def test_loop_repairs_then_falls_back_when_model_claims_unexecuted_mutation() -> None:
    turn = TurnExecution(session_id="session")
    responses = [_response("Criei App.tsx."), _response("Criei App.tsx com sucesso.")]

    with patch.object(
        handler,
        "_llm_call_with_learning",
        new=AsyncMock(side_effect=responses),
    ) as llm:
        content, _ = asyncio.run(
            handler.process_function_calls_loop(
                model="model",
                conversation_history=[],
                tool_schemas=[{"type": "function"}],
                available_tools={},
                stats=Mock(),
                ui=Mock(),
                console=Mock(),
                turn_execution=turn,
                user_request="Crie App.tsx",
            )
        )

    assert llm.await_count == 2
    assert (
        content
        == "Nenhuma operação foi executada; não posso confirmar a ação solicitada."
    )


def test_loop_stops_with_explicit_time_reason() -> None:
    from aura_cli.application.conversation.continuity import ContinuationController

    now = [0.0]
    controller = ContinuationController(max_seconds=60, clock=lambda: now[0])
    now[0] = 60.0

    content, response = asyncio.run(
        handler.process_function_calls_loop(
            model="model",
            conversation_history=[],
            tool_schemas=[],
            available_tools={},
            stats=Mock(),
            ui=Mock(),
            console=Mock(),
            continuation=controller,
        )
    )

    assert "limite de tempo" in content
    assert response is None
