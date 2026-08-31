from aura_cli.application.extensions import ExtensionHookManager, HookType


def test_hooks_execute_in_priority_order() -> None:
    ids = iter(["slow", "fast"])
    manager = ExtensionHookManager(id_factory=lambda: next(ids))
    manager.register_hook(HookType.BEFORE_TOOL_CALL, lambda ctx: "slow", priority=20)
    manager.register_hook(HookType.BEFORE_TOOL_CALL, lambda ctx: "fast", priority=10)

    assert manager.execute_hooks(HookType.BEFORE_TOOL_CALL, {}) == ["fast", "slow"]
    assert manager.list_hooks()["before_tool_call"][0]["hook_id"] == "fast"


def test_extension_hooks_can_be_removed_together() -> None:
    manager = ExtensionHookManager(id_factory=lambda: "hook")
    manager.register_hook(HookType.ON_STARTUP, lambda ctx: None, extension_name="one")
    manager.register_hook(HookType.ON_SHUTDOWN, lambda ctx: None, extension_name="one")

    assert manager.unregister_extension_hooks("one") == 2
    assert manager.get_hooks_count() == 0


def test_hook_failures_do_not_skip_later_callbacks() -> None:
    manager = ExtensionHookManager()

    def fail(_context):
        raise RuntimeError("broken")

    manager.register_hook(HookType.CUSTOM, fail)
    manager.register_hook(HookType.CUSTOM, lambda ctx: "healthy")

    assert manager.execute_hooks(HookType.CUSTOM) == ["healthy"]
