"""Core package of Aura CLI — fundamental system components.

Re-exports: config_manager, get_logger, cache_result, get_stats,
dependency analysis, and code-analysis helpers. All components are
thread-safe and designed for concurrent use.
"""

from aura_cli.core.cache import cache_result, clear_cache, get_cache_stats
from aura_cli.core.config import (
    CONFIG_DIR,
    CONFIG_FILE,
    DEFAULT_CONFIG,
    Config,
    config_manager,
    get_config_manager,
)
from aura_cli.core.di import (
    Container,
    Services,
    get_container,
    override,
    reset,
    resolve,
)
from aura_cli.core.di_bootstrap import bootstrap_services
from aura_cli.core.logger import (
    LOG_DIR,
    LOG_FILE,
    AuraFormatter,
    get_logger,
    setup_logger,
)
from aura_cli.core.stats import StatsTracker, get_stats, reset_stats


def __getattr__(name):
    """Lazy-load heavy submodules (code_analysis, dependency_analysis) on first access."""
    _code_analysis_exports = {
        "CodeClassification",
        "CodeSummary",
        "CodeTokenizer",
        "ComplexityLevel",
        "NLPAnalyzer",
        "TokenizationResult",
    }
    _dependency_analysis_exports = {
        "DependencyAnalyzer",
        "analyze_import_graph",
        "find_dependencies",
        "find_dependents",
        "get_impact_analysis",
    }

    if name in _code_analysis_exports:
        try:
            from aura_cli.core.code_analysis import (
                CodeClassification,
                CodeSummary,
                CodeTokenizer,
                ComplexityLevel,
                NLPAnalyzer,
                TokenizationResult,
            )

            return locals()[name]
        except ImportError:
            return None

    if name in _dependency_analysis_exports:
        try:
            from aura_cli.core.dependency_analysis import (
                DependencyAnalyzer,
                analyze_import_graph,
                find_dependencies,
                find_dependents,
                get_impact_analysis,
            )

            return locals()[name]
        except ImportError:
            return None

    raise AttributeError(f"module 'aura_cli.core' has no attribute {name!r}")


__all__ = [
    # Configuration
    "CONFIG_DIR",
    "CONFIG_FILE",
    "DEFAULT_CONFIG",
    # Logging
    "LOG_DIR",
    "LOG_FILE",
    "AuraFormatter",
    # Code Analysis
    "CodeClassification",
    "CodeSummary",
    "CodeTokenizer",
    "ComplexityLevel",
    "Config",
    # DI Container (primary API)
    "Container",
    # Dependency Analysis
    "DependencyAnalyzer",
    "NLPAnalyzer",
    "Services",
    # Statistics
    "StatsTracker",
    "TokenizationResult",
    "analyze_import_graph",
    "bootstrap_services",
    # Cache
    "cache_result",
    "clear_cache",
    "config_manager",
    "find_dependencies",
    "find_dependents",
    "get_cache_stats",
    "get_config_manager",
    "get_container",
    "get_impact_analysis",
    "get_logger",
    "get_stats",
    "override",
    "reset",
    "reset_stats",
    "resolve",
    "setup_logger",
]
