"""Priority-ordered callback hooks for application extensions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any, Callable, Optional
import uuid

logger = logging.getLogger(__name__)


class HookType(Enum):
    BEFORE_TOOL_CALL = "before_tool_call"
    AFTER_TOOL_CALL = "after_tool_call"
    BEFORE_AGENT_EXECUTE = "before_agent_execute"
    AFTER_AGENT_EXECUTE = "after_agent_execute"
    BEFORE_FILE_EDIT = "before_file_edit"
    AFTER_FILE_EDIT = "after_file_edit"
    ON_ERROR = "on_error"
    ON_STARTUP = "on_startup"
    ON_SHUTDOWN = "on_shutdown"
    CUSTOM = "custom"


@dataclass
class ExtensionHook:
    hook_id: str
    hook_type: HookType
    callback: Callable[[Any], Any]
    priority: int = 100
    extension_name: str = "system"


class ExtensionHookManager:
    """Register and execute extension callbacks in stable priority order."""

    def __init__(self, *, id_factory: Callable[[], str] | None = None) -> None:
        self.hooks: dict[HookType, list[ExtensionHook]] = {
            hook_type: [] for hook_type in HookType
        }
        self._id_factory = id_factory or (lambda: str(uuid.uuid4())[:8])

    def register_hook(
        self,
        hook_type: HookType,
        callback: Callable[[Any], Any],
        priority: int = 100,
        extension_name: str = "system",
    ) -> str:
        hook_id = self._id_factory()
        self.hooks[hook_type].append(
            ExtensionHook(
                hook_id=hook_id,
                hook_type=hook_type,
                callback=callback,
                priority=priority,
                extension_name=extension_name,
            )
        )
        self.hooks[hook_type].sort(key=lambda hook: hook.priority)
        return hook_id

    def execute_hooks(self, hook_type: HookType, context: Any = None) -> list[Any]:
        results: list[Any] = []
        for hook in self.hooks.get(hook_type, []):
            try:
                results.append(hook.callback(context))
            except Exception as exc:
                logger.error(
                    "Extension hook %s failed: %s", hook.hook_id, exc, exc_info=True
                )
        return results

    def unregister_hook(self, hook_id: str) -> bool:
        for hooks in self.hooks.values():
            for hook in hooks:
                if hook.hook_id == hook_id:
                    hooks.remove(hook)
                    return True
        return False

    def unregister_extension_hooks(self, extension_name: str) -> int:
        removed = 0
        for hook_type, hooks in self.hooks.items():
            retained = [hook for hook in hooks if hook.extension_name != extension_name]
            removed += len(hooks) - len(retained)
            self.hooks[hook_type] = retained
        return removed

    def get_hooks_count(self, hook_type: Optional[HookType] = None) -> int:
        if hook_type is not None:
            return len(self.hooks.get(hook_type, []))
        return sum(len(hooks) for hooks in self.hooks.values())

    def list_hooks(self) -> dict[str, list[dict[str, Any]]]:
        return {
            hook_type.value: [
                {
                    "hook_id": hook.hook_id,
                    "extension_name": hook.extension_name,
                    "priority": hook.priority,
                }
                for hook in hooks
            ]
            for hook_type, hooks in self.hooks.items()
        }
