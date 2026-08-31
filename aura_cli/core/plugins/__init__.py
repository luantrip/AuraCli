"""Built-in factory plugins loaded by default on every session.

These plugins are always active and are not intended to be uninstalled.
Drop-in user plugins live in the top-level ``extensions/`` directory instead.
"""

from aura_cli.core.plugins.auto_checkpoint import AutoCheckpointPlugin
from aura_cli.core.plugins.cost_tracker import CostTrackerPlugin
from aura_cli.core.plugins.security_guard import SecurityGuardPlugin

__all__ = [
    "AutoCheckpointPlugin",
    "CostTrackerPlugin",
    "SecurityGuardPlugin",
]

FACTORY_PLUGINS = [
    AutoCheckpointPlugin,
    CostTrackerPlugin,
    SecurityGuardPlugin,
]
