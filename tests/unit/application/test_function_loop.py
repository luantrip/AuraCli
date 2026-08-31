"""Application tests for the function-call turn state machine."""

import pytest

from aura_cli.application.conversation.function_loop import (
    FunctionLoopAction,
    FunctionLoopBudget,
    decide_function_loop_action,
)


@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        (
            {
                "has_response": False,
                "has_choices": False,
                "tool_call_count": 0,
                "content": None,
                "has_tool_schemas": False,
            },
            FunctionLoopAction.EMPTY_RESPONSE,
        ),
        (
            {
                "has_response": True,
                "has_choices": False,
                "tool_call_count": 0,
                "content": None,
                "has_tool_schemas": False,
            },
            FunctionLoopAction.INVALID_RESPONSE,
        ),
        (
            {
                "has_response": True,
                "has_choices": True,
                "tool_call_count": 2,
                "content": None,
                "has_tool_schemas": True,
            },
            FunctionLoopAction.EXECUTE_TOOLS,
        ),
        (
            {
                "has_response": True,
                "has_choices": True,
                "tool_call_count": 0,
                "content": None,
                "has_tool_schemas": True,
            },
            FunctionLoopAction.RETRY_WITHOUT_TOOLS,
        ),
        (
            {
                "has_response": True,
                "has_choices": True,
                "tool_call_count": 0,
                "content": "done",
                "has_tool_schemas": True,
            },
            FunctionLoopAction.RETURN_CONTENT,
        ),
    ],
)
def test_response_classification(inputs: dict, expected: FunctionLoopAction) -> None:
    assert decide_function_loop_action(**inputs) is expected


def test_budget_counts_individual_calls_and_validates_inputs() -> None:
    budget = FunctionLoopBudget(maximum=3)
    assert budget.consume(2) == 2
    assert budget.available
    assert budget.consume() == 3
    assert not budget.available
    with pytest.raises(ValueError):
        budget.consume(-1)
