"""Tool access policy system.

Provides granular tool access control with different permission levels.
"""

from dataclasses import dataclass, field
from enum import Enum
import threading
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
)

from aura_cli.contracts.security import ToolAccessDecision
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)


class AccessLevel(Enum):
    """Access level enum."""

    DENIED = "denied"  # Acesso negado
    READ_ONLY = "read_only"  # Apenas leitura
    LIMITED = "limited"  # Limitado
    FULL = "full"  # Acesso completo


@dataclass
class PolicyRule:
    """Policy rule (name, tool_pattern, access_level, conditions)."""

    name: str
    tool_pattern: str
    access_level: AccessLevel
    conditions: Optional[Callable[[Dict[str, Any]], bool]] = None
    description: str = ""


@dataclass
class ToolPolicy:
    """Tool access policy for an agent."""

    tool_name: str
    access_level: AccessLevel
    allowed_agents: Optional[Set[str]] = None
    denied_agents: Set[str] = field(default_factory=set)
    rate_limit: Optional[int] = None


class PolicyManager:
    """Manages tool access policies across agents."""

    def __init__(self):
        """Initialise the policy manager."""
        self.policies: Dict[str, ToolPolicy] = {}
        self.rules: List[PolicyRule] = []

        self.call_counts: Dict[str, List[float]] = {}
        self._rate_limit_lock = threading.Lock()

        logger.info("PolicyManager initialized")

    def add_policy(self, policy: ToolPolicy) -> None:
        """Register a tool policy for an agent."""
        self.policies[policy.tool_name] = policy
        logger.info(
            f"Política adicionada para ferramenta '{policy.tool_name}': "
            f"{policy.access_level.value}"
        )

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a rule to an existing policy."""
        self.rules.append(rule)
        logger.info(f"Regra de política '{rule.name}' adicionada")

    def check_access(
        self, tool_name: str, agent_id: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check whether an agent can access a tool."""
        return self._evaluate_access(
            tool_name, agent_id, parameters, consume_rate_limit=True
        ).as_legacy_tuple()

    def evaluate_access(
        self,
        tool_name: str,
        agent_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ToolAccessDecision:
        """Return typed access without consuming a rate-limit slot."""
        return self._evaluate_access(
            tool_name, agent_id, parameters, consume_rate_limit=False
        )

    def commit_access(
        self,
        tool_name: str,
        agent_id: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ToolAccessDecision:
        """Recheck access and consume one slot immediately before execution."""
        return self._evaluate_access(
            tool_name, agent_id, parameters, consume_rate_limit=True
        )

    def _evaluate_access(
        self,
        tool_name: str,
        agent_id: str,
        parameters: Optional[Dict[str, Any]],
        *,
        consume_rate_limit: bool,
    ) -> ToolAccessDecision:
        """Evaluate policy rules, optionally reserving one rate-limit slot."""
        if tool_name in self.policies:
            policy = self.policies[tool_name]

            if policy.access_level == AccessLevel.DENIED:
                return ToolAccessDecision(
                    False, f"Acesso negado à ferramenta '{tool_name}'"
                )

            if policy.allowed_agents and agent_id not in policy.allowed_agents:
                return ToolAccessDecision(
                    False,
                    f"Agente '{agent_id}' não tem permissão para '{tool_name}'",
                )

            if agent_id in policy.denied_agents:
                return ToolAccessDecision(
                    False, f"Agente '{agent_id}' está bloqueado para '{tool_name}'"
                )

            if policy.rate_limit:
                within_limit = (
                    self._check_rate_limit(tool_name, agent_id, policy.rate_limit)
                    if consume_rate_limit
                    else self._rate_limit_available(
                        tool_name, agent_id, policy.rate_limit
                    )
                )
                if not within_limit:
                    return ToolAccessDecision(
                        False, f"Rate limit excedido para '{tool_name}'"
                    )

        for rule in self.rules:
            import re

            if re.match(rule.tool_pattern, tool_name):
                if rule.conditions and parameters and not rule.conditions(parameters):
                    continue
                if rule.access_level == AccessLevel.DENIED:
                    return ToolAccessDecision(
                        False, f"Regra '{rule.name}' nega acesso a '{tool_name}'"
                    )
                if (
                    rule.access_level == AccessLevel.READ_ONLY
                    and parameters
                    and self._is_write_operation(parameters)
                ):
                    return ToolAccessDecision(
                        False,
                        f"Regra '{rule.name}' permite apenas leitura em '{tool_name}'",
                    )
        return ToolAccessDecision(True)

    def _rate_limit_available(self, tool_name: str, agent_id: str, limit: int) -> bool:
        """Check the current window without pruning or recording a call."""
        import time

        key = f"{tool_name}:{agent_id}"
        now = time.time()
        with self._rate_limit_lock:
            active_calls = [
                timestamp
                for timestamp in self.call_counts.get(key, [])
                if now - timestamp < 60.0
            ]
        return len(active_calls) < limit

    def _check_rate_limit(self, tool_name: str, agent_id: str, limit: int) -> bool:
        """Check and enforce the rate limit for a tool call."""
        import time

        key = f"{tool_name}:{agent_id}"
        now = time.time()
        with self._rate_limit_lock:
            if key in self.call_counts:
                self.call_counts[key] = [
                    t for t in self.call_counts[key] if now - t < 60.0
                ]
            else:
                self.call_counts[key] = []

            if len(self.call_counts[key]) >= limit:
                return False

            self.call_counts[key].append(now)
            return True

    def _is_write_operation(self, parameters: Dict[str, Any]) -> bool:
        """Return True if the tool name indicates a write operation."""
        write_keywords = ["write", "edit", "create", "delete", "update", "modify"]

        params_str = str(parameters).lower()
        return any(keyword in params_str for keyword in write_keywords)

    def get_statistics(self) -> Dict[str, Any]:
        """Return policy usage statistics as a dict."""
        return {
            "total_policies": len(self.policies),
            "total_rules": len(self.rules),
            "rate_limited_tools": len(self.call_counts),
        }
