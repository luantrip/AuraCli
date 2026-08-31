"""Aura Core Service Registry — canonical source of tools for the CLI.

Hierarchy:
  service_registry.py  → get_tools_dict() / get_standard_tools_map()
                         (all active tools, built from tool_manifest)
  tools_registry.py    → discovery engine (build-time)
  tools/unified_tool_registry.py → ADK-integrated registry

All code needing a tools dict should import from this module.
"""

from dataclasses import dataclass
from enum import Enum
import hashlib
import importlib
import json
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from aura_cli.core.cache_advanced.tool_result_cache import ToolResultCache
from aura_cli.core.logger import get_logger
from aura_cli.core.patterns.error_handling import handle_exceptions
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class ToolCategory(Enum):
    """Architectural classification for Aura functional tools."""

    FILE_SYSTEM = "file_system"
    DEVELOPMENT = "development"
    SHELL = "shell"
    WEB = "web"
    GIT = "git"
    DOCKER = "docker"
    MONITORING = "monitoring"
    INFRASTRUCTURE = "infrastructure"
    DATABASE = "database"
    SECURITY = "security"
    CI_CD = "ci_cd"
    TESTING = "testing"
    REFACTORING = "refactoring"
    ANALYSIS = "analysis"
    VISION = "vision"


class ToolEffect(Enum):
    """Observable side-effect classification for a tool."""

    READ_ONLY = "read_only"
    MUTATING = "mutating"


class ToolRisk(Enum):
    """Security review level declared when a tool is registered."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ToolDescriptor:
    """Encapsulates the definition and telemetry of a functional tool."""

    name: str
    category: ToolCategory
    description: str
    function: Callable
    schema: Dict[str, Any]
    effect: str = ToolEffect.MUTATING.value
    risk: str = ToolRisk.MEDIUM.value
    cacheable: bool = False
    enabled: bool = True
    usage_count: int = 0
    error_count: int = 0
    avg_execution_time: float = 0.0
    cache_ttl_seconds: Optional[int] = None


class LazyTool:
    """Callable proxy that resolves a tool implementation on first execution."""

    def __init__(
        self, name: str, module: str, qualname: str, schema: Dict[str, Any]
    ) -> None:
        self.__name__ = name
        self.__module__ = module
        self.__doc__ = schema.get("function", {}).get("description", "")
        self.__tool_schema__ = schema
        self._module = module
        self._qualname = qualname
        self._resolved: Optional[Callable[..., Any]] = None
        self._resolve_lock = threading.Lock()

    def resolve(self) -> Callable[..., Any]:
        """Import and cache the concrete implementation."""
        if self._resolved is None:
            with self._resolve_lock:
                if self._resolved is None:
                    target: Any = importlib.import_module(self._module)
                    for part in self._qualname.split("."):
                        target = getattr(target, part)
                    if not callable(target):
                        raise TypeError(
                            f"Tool {self.__name__!r} resolved to a non-callable object"
                        )
                    self._resolved = target
        return self._resolved

    @property
    def is_resolved(self) -> bool:
        """Whether the concrete implementation has already been imported."""
        return self._resolved is not None

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        return self.resolve()(*args, **kwargs)


class ServiceRegistry:
    """
    Standard registry for functional capabilities and core services.

    Orchestrates the lifecycle of Aura tools, providing a standardized execution
    environment with integrated caching and performance monitoring.
    """

    def __init__(self, cache_ttl_seconds: int = 300, cache_max_size: int = 1000):
        """
        Initializes the service registry engine.

        Args:
            cache_ttl_seconds: Default time-to-live for execution results.
            cache_max_size: Maximum capacity for the result cache.
        """
        self.tools: Dict[str, ToolDescriptor] = {}
        self.stats = get_stats()
        self._cache = ToolResultCache(
            default_ttl_seconds=cache_ttl_seconds,
            max_size=cache_max_size,
        )

        logger.info(
            f"Aura Core Service Registry active (Cache: {cache_ttl_seconds}s TTL, {cache_max_size} max size)"
        )

        self._bootstrap_registry()

    @handle_exceptions(Exception, default=None)
    def _bootstrap_registry(self):
        """Register descriptors without importing concrete implementations."""
        from aura_cli.core.tool_manifest import TOOL_MANIFEST

        for entry in TOOL_MANIFEST:
            self._register_tool(
                entry["name"],
                ToolCategory(entry["category"]),
                entry["description"],
                LazyTool(
                    entry["name"],
                    entry["module"],
                    entry["qualname"],
                    entry["schema"],
                ),
                entry["schema"],
                effect=entry["effect"],
                risk=entry.get("risk"),
                cacheable=entry["cacheable"],
            )
        count = len(TOOL_MANIFEST)
        logger.info(f"Successfully bootstrapped {count} standard library capabilities")

    def _register_tool(
        self,
        name: str,
        category: ToolCategory,
        description: str,
        function: Callable,
        schema: Dict[str, Any],
        *,
        effect: str = ToolEffect.MUTATING.value,
        risk: str | None = None,
        cacheable: bool = False,
    ):
        """Directly binds a tool to the registry (internal use only)."""
        if effect not in {item.value for item in ToolEffect}:
            raise ValueError(f"Unknown tool effect: {effect}")
        if risk is None:
            risk = (
                ToolRisk.LOW.value
                if effect == ToolEffect.READ_ONLY.value
                else ToolRisk.MEDIUM.value
            )
        if risk not in {item.value for item in ToolRisk}:
            raise ValueError(f"Unknown tool risk: {risk}")
        if effect == ToolEffect.MUTATING.value and cacheable:
            raise ValueError("Mutating tools cannot be cacheable")
        if not schema:
            try:
                from aura_cli.core.llm.tool_schemas import extract_function_schema

                schema = extract_function_schema(function)
            except Exception as e:
                logger.warning(f"Schema synthesis failure for '{name}': {e}")

        descriptor = ToolDescriptor(
            name=name,
            category=category,
            description=description,
            function=function,
            schema=schema,
            effect=effect,
            risk=risk,
            cacheable=cacheable,
        )

        self.tools[name] = descriptor
        logger.debug(f"Tool bound: {name} (Domain: {category.value})")

    def register_tool(
        self,
        name: str,
        category: ToolCategory,
        description: str,
        function: Callable,
        schema: Dict[str, Any],
        *,
        effect: ToolEffect,
        risk: ToolRisk,
        cacheable: bool = False,
    ) -> None:
        """Register an extension tool with explicit effect and risk metadata."""
        self._register_tool(
            name,
            category,
            description,
            function,
            schema,
            effect=effect.value,
            risk=risk.value,
            cacheable=cacheable,
        )

    def get_tool(self, name: str) -> Optional[ToolDescriptor]:
        """Resolves a tool descriptor by its identifier."""
        return self.tools.get(name)

    def get_all_tools(self) -> Dict[str, ToolDescriptor]:
        """Provides a complete map of registered tool descriptors."""
        return self.tools

    def get_tools_by_category(self, category: ToolCategory) -> List[ToolDescriptor]:
        """Filters the registry for capabilities within a specific architectural domain."""
        return [
            tool
            for tool in self.tools.values()
            if tool.category == category and tool.enabled
        ]

    def execute_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """
        Executes a functional capability with integrated caching and monitoring.

        Args:
            name: The target tool identifier.
            params: Parameters for the execution cycle.

        Returns:
            The execution result or None in case of failure/cancellation.
        """
        tool = self.get_tool(name)
        if tool is None:
            logger.error(f"Resolution fault: Tool '{name}' is not registered.")
            return None

        if not tool.enabled:
            logger.warning(f"Execution blocked: Tool '{name}' is currently disabled.")
            return None

        cache_key = None
        if tool.cacheable:
            # Cache is opt-in. Mutating and unreviewed tools always execute.
            serialized_params = json.dumps(
                params,
                sort_keys=True,
                separators=(",", ":"),
                default=repr,
            ).encode("utf-8")
            params_digest = hashlib.sha256(serialized_params).hexdigest()
            cache_key = f"tool_{name}_{params_digest}"
            cached_result = self._cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit: Reusing previous result for tool '{name}'")
                return cached_result

        try:
            start_time = time.time()
            result = tool.function(**params)
            execution_time = time.time() - start_time

            # Update telemetry and statistics
            tool.usage_count += 1
            tool.avg_execution_time = (
                tool.avg_execution_time * (tool.usage_count - 1) + execution_time
            ) / tool.usage_count
            self.stats.increment_tool_calls(name)

            # Persist to cache if applicable
            if cache_key is not None:
                self._cache.set(cache_key, result, ttl_seconds=tool.cache_ttl_seconds)

            logger.debug(f"Tool '{name}' execution finalized in {execution_time:.2f}s")
            return result

        except KeyboardInterrupt:
            tool.error_count += 1
            logger.info(f"Execution cycle for tool '{name}' interrupted by user.")
            return None
        except Exception as e:
            tool.error_count += 1
            from aura_cli.core.error_handler import get_error_handler
            from aura_cli.core.exceptions import ToolExecutionError

            error = ToolExecutionError(
                message=f"Fault during tool execution cycle: {name}",
                tool_name=name,
                tool_params=params,
                details=str(e),
            )

            get_error_handler().handle_error(
                error,
                context=f"runtime_tool:{name}",
                log=True,
                notify=False,
            )
            return None

    def get_telemetry_stats(self) -> Dict[str, Any]:
        """Provides high-level performance and usage telemetry for the tool ecosystem."""
        cache_stats = self._cache.get_stats()
        return {
            "total_capabilities": len(self.tools),
            "active_capabilities": sum(1 for t in self.tools.values() if t.enabled),
            "execution_metrics": {
                "total_calls": sum(t.usage_count for t in self.tools.values()),
                "fault_count": sum(t.error_count for t in self.tools.values()),
            },
            "domain_density": {
                cat.value: len(self.get_tools_by_category(cat)) for cat in ToolCategory
            },
            "hot_tools": sorted(
                [(t.name, t.usage_count) for t in self.tools.values()],
                key=lambda x: x[1],
                reverse=True,
            )[:10],
            "cache_state": cache_stats,
        }

    def flush_cache(self) -> None:
        """Clears all execution results from the internal cache."""
        self._cache.clear()
        logger.info("Service Registry cache flushed.")

    def cleanup_cache(self) -> int:
        """Removes expired entries from the result cache."""
        return self._cache.cleanup_expired()

    def get_tool_result_cache_stats(self) -> Dict[str, Any]:
        """Returns detailed cache statistics."""
        return self._cache.get_stats()

    def __len__(self) -> int:
        """Return the number of registered items."""
        return len(self.tools)


_registry: Optional[ServiceRegistry] = None
_registry_lock = threading.Lock()


def get_service_registry() -> ServiceRegistry:
    """Returns the singleton ServiceRegistry authority."""
    global _registry
    if _registry is None:
        with _registry_lock:
            if _registry is None:
                _registry = ServiceRegistry()
    return _registry


def get_capability_matrix():
    """Return the application-layer capability matrix from the canonical manifest."""
    from aura_cli.application.tools import CapabilityMatrix
    from aura_cli.core.tool_manifest import TOOL_MANIFEST

    return CapabilityMatrix.from_mappings(TOOL_MANIFEST)


def get_standard_tools_map() -> Dict[str, Callable]:
    """
    Exports the tool catalog as a functional map for standard orchestrations.

    Returns:
        A map of capability identifiers to their concrete Python implementations.
    """
    registry = get_service_registry()
    tools = registry.get_all_tools()
    result = {
        name: descriptor.function
        for name, descriptor in tools.items()
        if descriptor.enabled
    }
    from aura_cli.core.tools.arena_tools import arena_card, arena_status, arena_winner
    result.update({"arena_status": arena_status, "arena_winner": arena_winner, "arena_card": arena_card})
    return result


# Stable public composition name retained alongside the more explicit API.
get_tools_dict = get_standard_tools_map
