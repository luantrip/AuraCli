"""Neutral parsing of localized confirmation answers."""

YES_ANSWERS = frozenset(("y", "yes", "s", "sim", "a", "aceitar", "t"))
NO_ANSWERS = frozenset(("n", "no", "nao", "não", "r", "rejeitar"))


def parse_confirmation_answer(answer: str, default: bool) -> bool | None:
    """Return a decision or None when the answer is not recognized."""
    normalized = answer.strip().casefold()
    if normalized in YES_ANSWERS:
        return True
    if normalized in NO_ANSWERS:
        return False
    if not normalized:
        return default
    return None
