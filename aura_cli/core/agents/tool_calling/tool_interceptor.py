"""Tool call interception system.

Provides hooks to intercept, modify and monitor tool calls.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class HookType(Enum):
    """Tipos de hooks."""

    BEFORE = "before"  # Before execution
    AFTER = "after"  # After execution
    ERROR = "error"  # On error
    ALWAYS = "always"  # Sempre (antes e depois)


@dataclass
class InterceptorHook:
    """A hook registered with the tool interceptor."""

    id: str
    hook_type: HookType
    tool_pattern: Optional[str]
    handler: Callable
    priority: int = 5


@dataclass
class InterceptorResult:
    """Result returned by an interceptor hook."""

    intercepted: bool = False
    modified: bool = False
    cancelled: bool = False
    modified_parameters: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolInterceptor:
    """Intercepts tool calls for logging, validation and modification."""

    def __init__(self):
        """Initialise the interceptor."""
        self.hooks: List[InterceptorHook] = []
        self.stats = get_stats()

        self.total_interceptions = 0
        self.modifications = 0
        self.cancellations = 0

        logger.info("ToolInterceptor initialized")

    def register_hook(self, hook: InterceptorHook) -> None:
        """Register an interception hook."""
        self.hooks.append(hook)
        self.hooks.sort(key=lambda h: h.priority)

        logger.debug(
            f"Hook '{hook.id}' registrado "
            f"(tipo: {hook.hook_type.value}, prioridade: {hook.priority})"
        )

    def unregister_hook(self, hook_id: str) -> bool:
        """
        Remove um hook.

        Args:
            hook_id: ID do hook

        Returns:
            True if removed
        """
        original_count = len(self.hooks)
        self.hooks = [h for h in self.hooks if h.id != hook_id]

        removed = len(self.hooks) < original_count
        if removed:
            logger.debug(f"Hook '{hook_id}' removed")

        return removed

    def intercept_before(
        self, tool_name: str, parameters: Dict[str, Any]
    ) -> InterceptorResult:
        """Run pre-execution interceptors."""
        result = InterceptorResult()
        modified_params = parameters.copy()

        for hook in self.hooks:
            if hook.hook_type not in [HookType.BEFORE, HookType.ALWAYS]:
                continue

            if not self._matches_pattern(tool_name, hook.tool_pattern):
                continue

            try:
                hook_result = hook.handler(tool_name, modified_params, "before")

                if isinstance(hook_result, dict):
                    if hook_result.get("cancelled"):
                        result.cancelled = True
                        logger.info(
                            f"Chamada de '{tool_name}' cancelada por hook '{hook.id}'"
                        )
                        break

                    if hook_result.get("modified_parameters"):
                        modified_params = hook_result["modified_parameters"]
                        result.modified = True

                    if hook_result.get("metadata"):
                        result.metadata.update(hook_result["metadata"])

            except Exception as e:
                logger.error(f"Error executing hook '{hook.id}': {e}", exc_info=True)

        if result.modified:
            result.modified_parameters = modified_params
            self.modifications += 1

        if result.cancelled:
            self.cancellations += 1

        if result.intercepted or result.modified or result.cancelled:
            self.total_interceptions += 1

        return result

    def intercept_after(
        self, tool_name: str, parameters: Dict[str, Any], result: Any, success: bool
    ) -> InterceptorResult:
        """Run post-execution interceptors."""
        result_obj = InterceptorResult()

        hook_types = [HookType.AFTER, HookType.ALWAYS]
        if not success:
            hook_types.append(HookType.ERROR)

        for hook in self.hooks:
            if hook.hook_type not in hook_types:
                continue

            if not self._matches_pattern(tool_name, hook.tool_pattern):
                continue

            try:
                hook.handler(tool_name, parameters, "after", result, success)
            except Exception as e:
                logger.error(f"Error executing hook '{hook.id}': {e}", exc_info=True)

        result_obj.intercepted = True
        self.total_interceptions += 1

        return result_obj

    def _matches_pattern(self, tool_name: str, pattern: Optional[str]) -> bool:
        """Return True if a tool name matches an interceptor pattern."""
        if pattern is None:
            return True

        import re

        return bool(re.match(pattern, tool_name))

    def get_statistics(self) -> Dict[str, Any]:
        """Return interceptor statistics as a dict."""
        return {
            "total_hooks": len(self.hooks),
            "total_interceptions": self.total_interceptions,
            "modifications": self.modifications,
            "cancellations": self.cancellations,
        }
