"""Core extension API for the canonical lifecycle orchestration contracts."""

from aura_cli.application.extensions.lifecycle import (
    ExtensionLifecycle,
    LifecycleEvent,
    LifecycleHandler,
)

__all__ = ["ExtensionLifecycle", "LifecycleEvent", "LifecycleHandler"]
