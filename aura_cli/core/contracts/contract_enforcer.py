"""Runtime contract enforcement with BLOCK/WARN/LOG modes.

Loads YAML contract definitions and enforces them via the existing
``ExtensionHookManager`` before tool execution. Contracts can block unsafe
operations, warn on risky ones, or silently log for observability.

Inspired by the ``semantic-anchors`` plugin for OpenCode, adapted to
AuraCli's hook system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import logging
from pathlib import Path
import re
from typing import Any

import yaml

logger = logging.getLogger(__name__)


class ContractAction(str, Enum):
    BLOCK = "BLOCK"
    WARN = "WARN"
    LOG = "LOG"


@dataclass(frozen=True)
class Contract:
    """A single behavioural contract rule."""

    name: str
    trigger: str
    action: ContractAction
    message: str
    pattern: str | None = None
    condition: str | None = None

    def matches(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Check whether this contract applies to a tool call."""
        if self.trigger != tool_name:
            return False
        if self.pattern is not None:
            # Search pattern in all string values of arguments
            for value in arguments.values():
                if isinstance(value, str) and re.search(
                    self.pattern, value, re.IGNORECASE
                ):
                    return True
            return False
        if self.condition is not None:
            # Simple dotted-path condition evaluation: "args.force and args.branch == 'main'"
            # We evaluate against a namespace built from arguments.
            try:
                namespace = {"args": _ArgsNamespace(arguments)}
                # Disallow dangerous builtins
                eval_globals: dict[str, Any] = {"__builtins__": {}}
                return bool(eval(self.condition, {**eval_globals, **namespace}))
            except Exception:
                return False
        # No pattern or condition — matches any call to this trigger
        return True


class _ArgsNamespace:
    """Attribute-access wrapper for condition evaluation."""

    def __init__(self, data: dict[str, Any]) -> None:
        for key, value in data.items():
            setattr(self, key, value)

    def __getattr__(self, name: str) -> Any:
        return None


class ContractViolationError(Exception):
    """Raised when a BLOCK contract is violated."""

    def __init__(self, contract_name: str, message: str) -> None:
        self.contract_name = contract_name
        self.message = message
        super().__init__(f"[{contract_name}] {message}")


@dataclass
class ContractEnforcer:
    """Load, manage, and enforce runtime contracts.

    Integrate with ``ExtensionHookManager`` by registering the enforcer's
    ``check_before_tool_call`` method as a ``BEFORE_TOOL_CALL`` hook.
    """

    contracts: list[Contract] = field(default_factory=list)
    violation_log: list[dict[str, Any]] = field(default_factory=list)
    _log_limit: int = 500

    def add_contract(self, contract: Contract) -> None:
        self.contracts.append(contract)

    def load_contracts(self, yaml_path: str | Path) -> int:
        """Load contracts from a YAML file. Returns count loaded."""
        path = Path(yaml_path)
        if not path.exists():
            return 0
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not raw or not isinstance(raw, list):
            return 0
        count = 0
        for entry in raw:
            try:
                action = ContractAction(entry.get("action", "LOG"))
                contract = Contract(
                    name=entry["name"],
                    trigger=entry["trigger"],
                    action=action,
                    message=entry.get("message", ""),
                    pattern=entry.get("pattern"),
                    condition=entry.get("condition"),
                )
                self.add_contract(contract)
                count += 1
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping invalid contract entry: %s", exc)
        logger.info("Loaded %d contracts from %s", count, path)
        return count

    def load_profile(self, profile_name: str) -> int:
        """Load a built-in contract profile."""
        profile = _builtin_profiles().get(profile_name)
        if profile is None:
            logger.warning("Unknown contract profile: %s", profile_name)
            return 0
        for contract in profile:
            self.add_contract(contract)
        return len(profile)

    def check_before_tool_call(
        self, context: dict[str, Any]
    ) -> dict[str, Any] | ContractViolationError:
        """Hook callback for ``BEFORE_TOOL_CALL``.

        Returns the context unchanged if allowed. Raises
        ``ContractViolationError`` if a BLOCK contract matches.
        """
        tool_name = context.get("tool_name", "")
        arguments = context.get("arguments", {})

        for contract in self.contracts:
            if not contract.matches(tool_name, arguments):
                continue

            entry = {
                "contract": contract.name,
                "tool": tool_name,
                "action": contract.action.value,
                "message": contract.message,
                "timestamp": _now_iso(),
            }
            self._log_violation(entry)

            if contract.action is ContractAction.BLOCK:
                raise ContractViolationError(contract.name, contract.message)
            if contract.action is ContractAction.WARN:
                logger.warning(
                    "Contract WARN [%s]: %s — tool=%s",
                    contract.name,
                    contract.message,
                    tool_name,
                )
            # LOG: already recorded above
        return context

    def get_violation_log(self) -> list[dict[str, Any]]:
        """Return a copy of the violation log."""
        return self.violation_log.copy()

    def _log_violation(self, entry: dict[str, Any]) -> None:
        self.violation_log.append(entry)
        if len(self.violation_log) > self._log_limit:
            self.violation_log = self.violation_log[-self._log_limit :]

    @property
    def contract_count(self) -> int:
        return len(self.contracts)


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now().isoformat()


def _builtin_profiles() -> dict[str, list[Contract]]:
    """Return built-in contract profiles."""
    return {
        "agi-safe": [
            Contract(
                name="no-force-push-main",
                trigger="git_commit",
                action=ContractAction.BLOCK,
                message="Force push to main is blocked by contract",
                condition="args.force and args.get('branch', '') == 'main'",
            ),
            Contract(
                name="no-destructive-sql",
                trigger="run_shell_command",
                action=ContractAction.BLOCK,
                message="Destructive SQL blocked by contract",
                pattern=r"DROP\s+(DATABASE|TABLE|SCHEMA)",
            ),
            Contract(
                name="warn-large-delete",
                trigger="run_shell_command",
                action=ContractAction.WARN,
                message="Large recursive delete detected — verify path",
                pattern=r"rm\s+-rf\s+\.{2,}",
            ),
            Contract(
                name="no-format-c",
                trigger="run_shell_command",
                action=ContractAction.BLOCK,
                message="Formatting the C: drive is blocked",
                pattern=r"format\s+c:",
            ),
        ],
        "strict": [
            Contract(
                name="block-all-shell",
                trigger="run_shell_command",
                action=ContractAction.WARN,
                message="Shell execution requires explicit approval in strict mode",
            ),
            Contract(
                name="block-all-git",
                trigger="git_commit",
                action=ContractAction.WARN,
                message="Git operations require explicit approval in strict mode",
            ),
        ],
    }


__all__ = [
    "Contract",
    "ContractAction",
    "ContractEnforcer",
    "ContractViolationError",
]
