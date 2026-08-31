"""
Human Intervention Event System.

This module defines structured events for communication between workers
(OpsWorker, AgiWorker) and the UI when human intervention is required.
"""

from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional, Union
import uuid


class InterventionEventType(Enum):
    """Human intervention event types."""

    REQUEST = "human_intervention_request"
    RESPONSE = "human_intervention_response"
    TIMEOUT = "human_intervention_timeout"
    CANCELLED = "human_intervention_cancelled"


class InterventionRequestType(Enum):
    """Intervention request types."""

    CONFIRM = "confirm"
    INPUT = "input"
    PASSWORD = "password"
    SELECT_ONE = "select_one"
    SELECT_MANY = "select_many"
    MANUAL_STEP = "manual_step"


class RiskLevel(Enum):
    """Operation risk levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


RISK_CONFIG = {
    RiskLevel.LOW: {"color": "green", "icon": "ℹ️", "requires_confirmation": False},
    RiskLevel.MEDIUM: {"color": "yellow", "icon": "⚠️", "requires_confirmation": True},
    RiskLevel.HIGH: {"color": "red", "icon": "🔥", "requires_confirmation": True},
    RiskLevel.CRITICAL: {
        "color": "bright_red",
        "icon": "☠️",
        "requires_confirmation": True,
        "requires_double_confirm": True,
    },
}


@dataclass
class InterventionContext:
    """Context data for a human intervention request."""

    tool_name: Optional[str] = None
    tool_args: Optional[Dict[str, Any]] = None
    risk_level: RiskLevel = RiskLevel.MEDIUM
    description: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a dict."""
        return {
            "tool_name": self.tool_name,
            "tool_args": self.tool_args,
            "risk_level": (
                self.risk_level.value
                if isinstance(self.risk_level, RiskLevel)
                else self.risk_level
            ),
            "description": self.description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterventionContext":
        """Deserialise from a dict."""
        risk_level = data.get("risk_level", "medium")
        if isinstance(risk_level, str):
            risk_level = RiskLevel(risk_level)

        return cls(
            tool_name=data.get("tool_name"),
            tool_args=data.get("tool_args"),
            risk_level=risk_level,
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class InterventionRequest:
    """Human intervention request."""

    task_id: str
    request_id: str
    request_type: InterventionRequestType
    prompt: str
    context: InterventionContext
    options: Optional[List[str]] = None
    default: Optional[Union[str, bool]] = None
    timeout: Optional[int] = None
    timestamp: float = field(default_factory=time.time)

    placeholder: Optional[str] = None
    multiline: bool = False
    validator: Optional[str] = None

    instructions: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a dict."""
        return {
            "type": InterventionEventType.REQUEST.value,
            "task_id": self.task_id,
            "request_id": self.request_id,
            "request_type": (
                self.request_type.value
                if isinstance(self.request_type, InterventionRequestType)
                else self.request_type
            ),
            "prompt": self.prompt,
            "context": self.context.to_dict(),
            "options": self.options,
            "default": self.default,
            "timeout": self.timeout,
            "timestamp": self.timestamp,
            "placeholder": self.placeholder,
            "multiline": self.multiline,
            "validator": self.validator,
            "instructions": self.instructions,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterventionRequest":
        """Deserialise from a dict."""
        request_type = data.get("request_type", "confirm")
        if isinstance(request_type, str):
            request_type = InterventionRequestType(request_type)

        context_data = data.get("context", {})
        context = (
            InterventionContext.from_dict(context_data)
            if context_data
            else InterventionContext()
        )

        return cls(
            task_id=data["task_id"],
            request_id=data["request_id"],
            request_type=request_type,
            prompt=data["prompt"],
            context=context,
            options=data.get("options"),
            default=data.get("default"),
            timeout=data.get("timeout"),
            timestamp=data.get("timestamp", time.time()),
            placeholder=data.get("placeholder"),
            multiline=data.get("multiline", False),
            validator=data.get("validator"),
            instructions=data.get("instructions"),
        )


@dataclass
class InterventionResponse:
    """Human intervention response."""

    task_id: str
    request_id: str
    approved: bool
    value: Optional[Union[str, List[str], bool]] = None
    cancelled: bool = False
    reason: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise to a dict."""
        return {
            "type": InterventionEventType.RESPONSE.value,
            "task_id": self.task_id,
            "request_id": self.request_id,
            "approved": self.approved,
            "value": self.value,
            "cancelled": self.cancelled,
            "reason": self.reason,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InterventionResponse":
        """Deserialise from a dict."""
        return cls(
            task_id=data["task_id"],
            request_id=data["request_id"],
            approved=data.get("approved", False),
            value=data.get("value"),
            cancelled=data.get("cancelled", False),
            reason=data.get("reason"),
            timestamp=data.get("timestamp", time.time()),
        )


def create_confirmation_request(
    task_id: str,
    prompt: str,
    context: Optional[InterventionContext] = None,
    default: bool = False,
    timeout: Optional[int] = 60,
) -> Dict[str, Any]:
    """Create a confirmation intervention request."""
    request = InterventionRequest(
        task_id=task_id,
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        request_type=InterventionRequestType.CONFIRM,
        prompt=prompt,
        context=context or InterventionContext(),
        options=["Sim", "Não"],
        default="Sim" if default else "Não",
        timeout=timeout,
    )
    return request.to_dict()


def create_input_request(
    task_id: str,
    prompt: str,
    placeholder: Optional[str] = None,
    default: Optional[str] = None,
    multiline: bool = False,
    validator: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a free-text input intervention request."""
    request = InterventionRequest(
        task_id=task_id,
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        request_type=InterventionRequestType.INPUT,
        prompt=prompt,
        context=InterventionContext(),
        placeholder=placeholder,
        default=default,
        multiline=multiline,
        validator=validator,
        timeout=timeout,
    )
    return request.to_dict()


def create_password_request(
    task_id: str, prompt: str, timeout: Optional[int] = 120
) -> Dict[str, Any]:
    """Create a password input intervention request."""
    request = InterventionRequest(
        task_id=task_id,
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        request_type=InterventionRequestType.PASSWORD,
        prompt=prompt,
        context=InterventionContext(risk_level=RiskLevel.HIGH),
        timeout=timeout,
    )
    return request.to_dict()


def create_selection_request(
    task_id: str,
    prompt: str,
    options: List[str],
    multiple: bool = False,
    default: Optional[Union[str, List[str]]] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """Create a selection intervention request."""
    request_type = (
        InterventionRequestType.SELECT_MANY
        if multiple
        else InterventionRequestType.SELECT_ONE
    )

    request = InterventionRequest(
        task_id=task_id,
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        request_type=request_type,
        prompt=prompt,
        context=InterventionContext(),
        options=options,
        default=default,  # type: ignore[arg-type]
        timeout=timeout,
    )
    return request.to_dict()


def create_manual_step_request(
    task_id: str, prompt: str, instructions: List[str], timeout: Optional[int] = 300
) -> Dict[str, Any]:
    """Create a manual-step intervention request."""
    request = InterventionRequest(
        task_id=task_id,
        request_id=f"req_{uuid.uuid4().hex[:8]}",
        request_type=InterventionRequestType.MANUAL_STEP,
        prompt=prompt,
        context=InterventionContext(),
        instructions=instructions,
        timeout=timeout,
    )
    return request.to_dict()


def create_response(
    task_id: str,
    request_id: str,
    approved: bool,
    value: Optional[Union[str, List[str], bool]] = None,
    cancelled: bool = False,
    reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Create an intervention response."""
    response = InterventionResponse(
        task_id=task_id,
        request_id=request_id,
        approved=approved,
        value=value,
        cancelled=cancelled,
        reason=reason,
    )
    return response.to_dict()
