"""
Constants used throughout the Aura CLI application.

This module centralizes all magic numbers and configuration values
to improve maintainability and make values easily configurable.
"""

MAX_LLM_RETRIES: int = 3
MAX_BACKOFF_SECONDS: float = 60.0

# Tool-call budget per interactive turn (chat mode).
# AGI/Ops workers override this via their own config.
# 100 was the original value — way too high for interactive use: a runaway
# agent could burn tokens for minutes before the user noticed.
MAX_FUNCTION_CALLS: int = 15

DEFAULT_LLM_TIMEOUT: float = 30.0

# Hard cap for autonomous agent iterations (AGI/Ops workers).
# 100 was dangerously high — 30 covers complex multi-step tasks without
# allowing unbounded loops.
MAX_AGENT_ITERATIONS: int = 30

DEFAULT_SHELL_TIMEOUT: int = 30
LONG_SHELL_TIMEOUT: int = 300

MAX_HISTORY_SIZE: int = 100
COMPRESSION_THRESHOLD: int = 40
DEFAULT_WORKER_TIMEOUT: float = 60.0
MAX_QUEUE_TIMEOUT: float = 300.0
SHORT_STATUS_TIMEOUT: float = 0.5
MEDIUM_STATUS_TIMEOUT: float = 10.0
THREAD_JOIN_TIMEOUT: float = 2.0
WORKER_SHUTDOWN_TIMEOUT: float = 5.0

MAX_EVENT_QUEUE_SIZE: int = 1000
MAX_EVENT_HISTORY: int = 500

FALLBACK_CHARS_PER_TOKEN: float = 4.0
