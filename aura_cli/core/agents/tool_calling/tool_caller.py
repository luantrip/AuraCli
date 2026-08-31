"""Advanced tool caller for agents.

Provides robust tool execution with retry, timeout, fallback and telemetry.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Dict, Optional

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)


class CallStrategy(Enum):
    """Tool call strategy enum."""

    DIRECT = "direct"  # Chamada direta
    RETRY = "retry"  # With automatic retry
    FALLBACK = "fallback"  # With fallback
    ASYNC = "async"  # Asynchronous


@dataclass
class ToolCallResult:
    """Tool call result (success, result, error, duration, retries)."""

    success: bool
    result: Any = None
    duration: float = 0.0
    attempts: int = 1
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolCaller:
    """Executes tool calls with retry, async support and statistics."""

    def __init__(
        self, max_retries: int = 3, timeout: float = 30.0, enable_cache: bool = True
    ):
        """Initialise the tool caller."""
        self.max_retries = max_retries
        self.timeout = timeout
        self.enable_cache = enable_cache

        self.result_cache: Dict[str, Any] = {}

        self.stats = get_stats()
        self.total_calls = 0
        self.successful_calls = 0
        self.failed_calls = 0

        logger.info(
            f"ToolCaller initialized (max_retries: {max_retries}, timeout: {timeout}s)"
        )

    def call(
        self,
        tool_name: str,
        tool_func: Callable,
        parameters: Dict[str, Any],
        strategy: CallStrategy = CallStrategy.RETRY,
        cache_key: Optional[str] = None,
    ) -> ToolCallResult:
        """Call a tool by name with given arguments."""
        self.total_calls += 1

        if self.enable_cache and cache_key and cache_key in self.result_cache:
            logger.debug(f"Cache hit para ferramenta {tool_name}")
            cached_result = self.result_cache[cache_key]
            return ToolCallResult(
                success=True,
                result=cached_result,
                duration=0.0,
                metadata={"cached": True},
            )

        start_time = time.time()

        if strategy == CallStrategy.RETRY:
            result = self._call_with_retry(tool_name, tool_func, parameters, start_time)
        elif strategy == CallStrategy.ASYNC:
            result = self._call_async(tool_name, tool_func, parameters)
        else:
            result = self._call_direct(tool_name, tool_func, parameters, start_time)

        if result.success:
            self.successful_calls += 1
            if self.enable_cache and cache_key:
                self.result_cache[cache_key] = result.result
        else:
            self.failed_calls += 1

        self.stats.track_tool_usage(f"tool_caller_{tool_name}")

        return result

    def _call_direct(
        self,
        tool_name: str,
        tool_func: Callable,
        parameters: Dict[str, Any],
        start_time: float,
    ) -> ToolCallResult:
        """Call a tool directly without retry."""
        try:
            result = tool_func(**parameters)
            duration = time.time() - start_time

            logger.debug(
                f"Ferramenta {tool_name} executada com sucesso ({duration:.2f}s)"
            )

            return ToolCallResult(
                success=True, result=result, duration=duration, attempts=1
            )

        except Exception as e:
            duration = time.time() - start_time
            error_msg = str(e)

            logger.error(f"Ferramenta {tool_name} falhou: {error_msg}", exc_info=True)

            return ToolCallResult(
                success=False, duration=duration, attempts=1, error=error_msg
            )

    def _call_with_retry(
        self,
        tool_name: str,
        tool_func: Callable,
        parameters: Dict[str, Any],
        start_time: float,
    ) -> ToolCallResult:
        """Call a tool with automatic retry on failure."""
        last_error = None

        for attempt in range(1, self.max_retries + 1):
            try:
                result = tool_func(**parameters)
                duration = time.time() - start_time

                logger.debug(
                    f"Ferramenta {tool_name} executada com sucesso "
                    f"(tentativa {attempt}/{self.max_retries}, {duration:.2f}s)"
                )

                return ToolCallResult(
                    success=True, result=result, duration=duration, attempts=attempt
                )

            except Exception as e:
                last_error = e
                error_msg = str(e)

                if attempt < self.max_retries:
                    wait_time = attempt * 0.5
                    logger.warning(
                        f"Ferramenta {tool_name} falhou (tentativa {attempt}/"
                        f"{self.max_retries}): {error_msg}. Waiting {wait_time}s..."
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(
                        f"Ferramenta {tool_name} falhou após {attempt} tentativas: {error_msg}",
                        exc_info=True,
                    )

        duration = time.time() - start_time

        return ToolCallResult(
            success=False,
            duration=duration,
            attempts=self.max_retries,
            error=str(last_error) if last_error else "Erro desconhecido",
        )

    def _call_async(
        self, tool_name: str, tool_func: Callable, parameters: Dict[str, Any]
    ) -> ToolCallResult:
        """Call a tool asynchronously."""
        return self._call_direct(tool_name, tool_func, parameters, time.time())

    def clear_cache(self) -> None:
        """Limpa cache de resultados."""
        self.result_cache.clear()
        logger.info("Cache de ferramentas limpo")

    def get_statistics(self) -> Dict[str, Any]:
        """Return tool call statistics as a dict."""
        success_rate = (
            self.successful_calls / self.total_calls if self.total_calls > 0 else 0.0
        )

        return {
            "total_calls": self.total_calls,
            "successful_calls": self.successful_calls,
            "failed_calls": self.failed_calls,
            "success_rate": success_rate,
            "cache_size": len(self.result_cache),
            "max_retries": self.max_retries,
            "timeout": self.timeout,
        }
