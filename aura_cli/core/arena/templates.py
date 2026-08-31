"""Prompt templates used by ArenaEngine integrations."""

COMPETITOR_TEMPLATE = """Solve this task independently. Apply the assigned strategy card.
Task:
{task}

Strategy card:
{card}
Return a complete proposed solution and its assumptions."""

JUDGE_TEMPLATE = """Compare two candidate solutions for the task below. Score each from 0 to 10
on correctness, completeness, robustness, specificity, and clarity. Return JSON with
scores, winner (agent id), and a concise reason.
Task: {task}
Candidate A ({agent_a}): {solution_a}
Candidate B ({agent_b}): {solution_b}"""
