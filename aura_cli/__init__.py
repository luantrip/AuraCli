"""
Aura CLI - AI code assistant with integrated tools.
"""

__version__ = "0.1.0"
__author__ = "Luan"
__email__ = "luan@udesc.br"

# Lightweight core exports (always available)
from aura_cli.core import Config, get_logger, get_stats
from aura_cli.core.stats import StatsTracker


def __getattr__(name):
    """Lazy-load optional heavy exports on first access."""
    if name == "DependencyAnalyzer":
        try:
            from aura_cli.core.dependency_analysis import DependencyAnalyzer

            return DependencyAnalyzer
        except ImportError:
            return None
    raise AttributeError(f"module 'aura_cli' has no attribute {name!r}")


__all__ = [
    # Core exports
    "Config",
    "DependencyAnalyzer",
    "StatsTracker",
    "__author__",
    "__email__",
    "__version__",
    "get_logger",
    "get_stats",
]
