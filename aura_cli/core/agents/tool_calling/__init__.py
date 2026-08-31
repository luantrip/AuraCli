"""Advanced tool-calling system for Aura CLI agents.

Re-exports ToolCaller (sync/async/parallel strategies), ToolPolicy (role-based
access control), ToolValidator (parameter schema validation), ChainExecutor /
ChainLink (sequential tool chains) and ToolInterceptor (logging/modification).
"""

from aura_cli.core.agents.tool_calling.tool_caller import (
    CallStrategy,
    ToolCaller,
    ToolCallResult,
)
from aura_cli.core.agents.tool_calling.tool_chain import (
    ChainExecutor,
    ChainLink,
    ToolChain,
)
from aura_cli.core.agents.tool_calling.tool_interceptor import (
    InterceptorHook,
    InterceptorResult,
    ToolInterceptor,
)
from aura_cli.core.agents.tool_calling.tool_policies import (
    AccessLevel,
    PolicyManager,
    PolicyRule,
    ToolPolicy,
)
from aura_cli.core.agents.tool_calling.tool_validator import (
    ToolSchema,
    ToolValidator,
    ValidationError,
)

__all__ = [
    "AccessLevel",
    "CallStrategy",
    "ChainExecutor",
    "ChainLink",
    "InterceptorHook",
    "InterceptorResult",
    "PolicyManager",
    "PolicyRule",
    "ToolCallResult",
    "ToolCaller",
    "ToolChain",
    "ToolInterceptor",
    "ToolPolicy",
    "ToolSchema",
    "ToolValidator",
    "ValidationError",
]
