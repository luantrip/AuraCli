"""
Hook manager for event-driven extensibility.

Allows executing custom commands at specific lifecycle points.
"""

import asyncio
from collections import defaultdict
import contextlib
from datetime import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from aura_cli.application.extensions.subprocess_hooks import (
    CommandHook as Hook,
)
from aura_cli.application.extensions.subprocess_hooks import (
    HookEvent,
    HookResult,
    hook_cache_key,
    hook_matches,
)


class HookManager:
    """Event-driven hook manager for extensibility.

    Supports AgentSpawn, UserPromptSubmit, PreToolUse (can block),
    PostToolUse and Stop events. Hooks are registered via register()
    and fired via await trigger(event, context). Results are cached
    per tool-name match.
    """

    def __init__(self):
        """Initialize the instance."""
        self.hooks: Dict[HookEvent, List[Hook]] = defaultdict(list)
        self.cache: Dict[str, tuple[HookResult, datetime]] = {}

    def register(self, hook: Hook):
        """Register a hook."""
        self.hooks[hook.event].append(hook)

    def load_from_file(self, config_path: Path):
        """
        Load hooks from JSON config file.

        Format:
        {
          "hooks": [
            {
              "type": "PreToolUse",
              "matcher": "write_file",
              "command": ["python3", "validate.py"],
              "timeout_ms": 5000
            }
          ]
        }
        """
        if not config_path.exists():
            return

        with open(config_path) as f:
            config = json.load(f)

        for hook_config in config.get("hooks", []):
            event_type = hook_config.get("type")
            event_map = {
                "AgentSpawn": HookEvent.AGENT_SPAWN,
                "UserPromptSubmit": HookEvent.USER_PROMPT,
                "PreToolUse": HookEvent.PRE_TOOL,
                "PostToolUse": HookEvent.POST_TOOL,
                "Stop": HookEvent.STOP,
            }

            event = event_map.get(event_type)
            if not event:
                continue

            hook = Hook(
                event=event,
                command=hook_config.get("command", []),
                matcher=hook_config.get("matcher"),
                timeout_ms=hook_config.get("timeout_ms", 30000),
                cache_ttl_seconds=hook_config.get("cache_ttl_seconds", 0),
            )

            self.register(hook)

    async def trigger(self, event: HookEvent, context: Dict[str, Any]) -> HookResult:
        """
        Trigger hooks for event.

        Args:
            event: Hook event type
            context: Event context (tool_name, tool_input, etc.)

        Returns:
            HookResult with combined results
        """
        hooks = self.hooks.get(event, [])

        for hook in hooks:
            if not self._matches(hook, context):
                continue

            if hook.cache_ttl_seconds > 0 and event != HookEvent.AGENT_SPAWN:
                cache_key = self._get_cache_key(hook, context)
                cached = self._get_cached(cache_key, hook.cache_ttl_seconds)
                if cached:
                    return cached

            result = await self._execute_hook(hook, context)

            if result.success and hook.cache_ttl_seconds > 0:
                cache_key = self._get_cache_key(hook, context)
                self.cache[cache_key] = (result, datetime.now())

            if result.should_block and event == HookEvent.PRE_TOOL:
                return HookResult(exit_code=2, stderr=result.stderr, blocked=True)
            elif not result.success:
                from aura_cli.core.logger import get_logger

                logger = get_logger(__name__)
                logger.warning(f"Hook failed: {result.stderr}")

        return HookResult(exit_code=0)

    def _matches(self, hook: Hook, context: Dict[str, Any]) -> bool:
        """Check if hook matches context."""
        return hook_matches(hook, context)

    async def _execute_hook(self, hook: Hook, context: Dict[str, Any]) -> HookResult:
        """Execute hook command."""
        hook_input = json.dumps(
            {"hook_event_name": hook.event.value, "cwd": os.getcwd(), **context}
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *hook.command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(hook_input.encode()), timeout=hook.timeout_ms / 1000
            )

            return HookResult(
                exit_code=proc.returncode or 0,
                stdout=stdout.decode(),
                stderr=stderr.decode(),
            )

        except asyncio.TimeoutError:
            with contextlib.suppress(Exception):
                proc.kill()
            return HookResult(exit_code=1, stderr="Hook timeout")
        except Exception as e:
            return HookResult(exit_code=1, stderr=str(e))

    def _get_cache_key(self, hook: Hook, context: Dict[str, Any]) -> str:
        """Generate cache key."""
        return hook_cache_key(hook, context)

    def _get_cached(self, key: str, ttl_seconds: int) -> Optional[HookResult]:
        """Get cached result if valid."""
        if key not in self.cache:
            return None

        result, timestamp = self.cache[key]
        age = (datetime.now() - timestamp).total_seconds()

        if age > ttl_seconds:
            del self.cache[key]
            return None

        return result

    def clear_cache(self):
        """Clear hook cache."""
        self.cache.clear()


_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get the global HookManager instance."""
    # Try DI container first (preferred path)
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.HOOK_MANAGER):
            return container.resolve(Services.HOOK_MANAGER)
    except Exception:
        pass

    # Fallback to legacy singleton
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager
