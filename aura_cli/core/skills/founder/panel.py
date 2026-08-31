"""Deterministic simulated-buyer panel primitives."""

from __future__ import annotations

from collections import Counter
import random
from typing import Any


class PanelError(ValueError):
    """Raised when a customer profile or answer is invalid."""


def _quota(items: list[dict[str, Any]], count: int) -> list[int]:
    total = sum(float(item.get("share", 1)) for item in items) or 1.0
    raw = [count * float(item.get("share", 1)) / total for item in items]
    result = [int(value) for value in raw]
    for index in sorted(
        range(len(items)), key=lambda i: raw[i] - result[i], reverse=True
    )[: count - sum(result)]:
        result[index] += 1
    return result


def deal_buyers(
    customer: dict[str, Any], count: int = 20, seed: int = 7
) -> list[dict[str, Any]]:
    """Deal reproducible buyer profiles from a validated customer definition."""
    required = ("business", "target", "segments", "behaviours", "objections")
    if count < 1 or any(not customer.get(field) for field in required):
        raise PanelError("customer profile is incomplete")
    if any(len(segment.get("income", [])) != 2 for segment in customer["segments"]):
        raise PanelError("each segment needs income [low, high]")
    rng = random.Random(seed)
    segments = [
        segment
        for segment, quota in zip(
            customer["segments"], _quota(customer["segments"], count), strict=True
        )
        for _ in range(quota)
    ]
    behaviours = [
        behaviour
        for behaviour, quota in zip(
            customer["behaviours"], _quota(customer["behaviours"], count), strict=True
        )
        for _ in range(quota)
    ]
    rng.shuffle(segments)
    rng.shuffle(behaviours)
    age = customer.get("age", [25, 45])
    buyers = []
    for index in range(count):
        segment = segments[index]
        low, high = segment["income"]
        behaviour = behaviours[index]
        buyers.append(
            {
                "id": f"P{index + 1:03d}",
                "name": f"Buyer {index + 1:03d}",
                "age": rng.randint(int(age[0]), int(age[1])),
                "segment": segment["name"],
                "income": int(round(rng.uniform(float(low), float(high)), -2)),
                "behaviour": behaviour["name"],
                "behaviour_how": behaviour.get("how", ""),
                "objection": rng.choice(customer["objections"]),
            }
        )
    return buyers


def tally_answers(answers: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize validated buyer answers without inventing missing responses."""
    valid = []
    skipped = []
    for answer in answers:
        if (
            not isinstance(answer, dict)
            or not isinstance(answer.get("buys"), bool)
            or not answer.get("id")
        ):
            skipped.append(
                answer.get("id", "unknown") if isinstance(answer, dict) else "unknown"
            )
        else:
            valid.append(answer)
    buys = sum(answer["buys"] for answer in valid)
    reasons = Counter(
        answer.get("reason_code", "other") for answer in valid if not answer["buys"]
    )
    return {
        "buys": buys,
        "passes": len(valid) - buys,
        "answered": len(valid),
        "buy_rate": buys / len(valid) if valid else 0.0,
        "why_not": reasons.most_common(),
        "skipped": skipped,
    }
