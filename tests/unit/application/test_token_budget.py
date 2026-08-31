from aura_cli.application.conversation.budget import BudgetDecision, TokenBudget


def test_token_budget_distinguishes_continue_compact_and_stop() -> None:
    budget = TokenBudget(80, 100, 800, 1000)

    assert (
        budget.decide(context_tokens=10, session_tokens=20) is BudgetDecision.CONTINUE
    )
    assert budget.decide(context_tokens=80, session_tokens=20) is BudgetDecision.COMPACT
    assert (
        budget.decide(context_tokens=10, session_tokens=800) is BudgetDecision.COMPACT
    )
    assert budget.decide(context_tokens=100, session_tokens=20) is BudgetDecision.STOP
    assert budget.decide(context_tokens=10, session_tokens=1000) is BudgetDecision.STOP
