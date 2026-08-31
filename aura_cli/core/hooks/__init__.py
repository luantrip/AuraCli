"""
Hooks system for Aura CLI.

Event-driven hooks for intercepting and extending agent behavior.
Inspired by Kiro CLI's hooks system.
"""

from aura_cli.core.hooks.manager import Hook, HookEvent, HookManager, HookResult

__all__ = ["Hook", "HookEvent", "HookManager", "HookResult"]
