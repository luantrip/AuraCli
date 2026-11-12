"""``LLMQueryMixin._context_hard_limit`` wiring contracts.

Resolves the active model (default_model, else final_model) and honors an explicit
``context_max_tokens`` override. Tested in isolation via a minimal stub so no full
handler is constructed; the method only reads ``self.final_model`` and the shared
``config_manager``.
"""

from __future__ import annotations

import pytest

from aura_cli.application.workspace import context_hard_limit_for_model


def _limit(monkeypatch, *, default_model, final_model, override):
    import aura_cli.cli.llm_handler as handler_mod
    from aura_cli.cli.llm_handler import LLMQueryMixin

    values = {"default_model": default_model, "context_max_tokens": override}
    monkeypatch.setattr(
        handler_mod.config_manager,
        "get",
        lambda key, default=None: values.get(key, default),
    )

    class _Stub:
        pass

    stub = _Stub()
    stub.final_model = final_model
    return LLMQueryMixin._context_hard_limit(stub)


def test_uses_default_model_when_configured(monkeypatch) -> None:
    limit = _limit(
        monkeypatch, default_model="gemini-2.5-pro", final_model="gpt-4o", override=None
    )
    assert limit == context_hard_limit_for_model("gemini-2.5-pro")


def test_falls_back_to_final_model_when_no_default(monkeypatch) -> None:
    limit = _limit(monkeypatch, default_model=None, final_model="gpt-4o", override=None)
    assert limit == context_hard_limit_for_model("gpt-4o")


def test_explicit_override_is_honored(monkeypatch) -> None:
    limit = _limit(
        monkeypatch,
        default_model="gemini-2.5-pro",
        final_model="gpt-4o",
        override=40_000,
    )
    assert limit == 40_000


def test_garbage_override_is_ignored(monkeypatch) -> None:
    limit = _limit(
        monkeypatch,
        default_model=None,
        final_model="gpt-4o",
        override="not-a-number",
    )
    assert limit == context_hard_limit_for_model("gpt-4o")


@pytest.mark.parametrize("override", [None, 0, -10])
def test_non_positive_override_uses_the_per_model_budget(monkeypatch, override) -> None:
    limit = _limit(
        monkeypatch, default_model=None, final_model="gemini-2.5-pro", override=override
    )
    assert limit == context_hard_limit_for_model("gemini-2.5-pro")
    assert limit > 32_000  # the regression target: no longer a fixed 32k
