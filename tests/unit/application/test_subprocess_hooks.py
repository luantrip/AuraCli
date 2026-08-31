import pytest

from aura_cli.application.extensions import (
    CommandHook,
    HookEvent,
    HookResult,
    hook_cache_key,
    hook_matches,
)


def test_hook_matching_supports_exact_glob_and_server_scope() -> None:
    context = {"tool_name": "@files/read_file"}

    assert hook_matches(CommandHook(HookEvent.PRE_TOOL, ["check"], "@files"), context)
    assert hook_matches(
        CommandHook(HookEvent.PRE_TOOL, ["check"], "@*/read_*"), context
    )
    assert not hook_matches(
        CommandHook(HookEvent.PRE_TOOL, ["check"], "write_file"), context
    )


def test_hook_cache_key_is_stable_for_context_order() -> None:
    hook = CommandHook(HookEvent.POST_TOOL, ["python", "hook.py"])

    assert hook_cache_key(hook, {"b": 2, "a": 1}) == hook_cache_key(
        hook, {"a": 1, "b": 2}
    )


def test_hook_result_exposes_success_and_blocking_semantics() -> None:
    assert HookResult(0).success is True
    assert HookResult(2).should_block is True


@pytest.mark.parametrize(
    ("timeout", "ttl", "message"),
    [(0, 0, "timeout"), (1, -1, "TTL")],
)
def test_hook_configuration_rejects_invalid_limits(timeout, ttl, message) -> None:
    with pytest.raises(ValueError, match=message):
        CommandHook(
            HookEvent.PRE_TOOL,
            ["check"],
            timeout_ms=timeout,
            cache_ttl_seconds=ttl,
        )
