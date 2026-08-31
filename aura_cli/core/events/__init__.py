"""
Event system for inter-component communication.

This package provides:
- AgiEvents: Structured events for AGI task lifecycle
- HumanInterventionEvents: Events for human interaction requests
- CoreEventBus: Centralized thread-safe event bus
- EventContracts: Unified Pydantic payload schemas (single source of truth)
"""

from aura_cli.core.events.agi_events import (
    AgiEvent,
    AgiEventType,
    AgiTaskCompleteEvent,
    AgiTaskStartEvent,
    AgiTaskUpdateEvent,
    CapabilityDecisionEvent,
    ChatMessageEvent,
    LifecycleEvent,
    ToolExecutingEvent,
    ToolResultEvent,
    create_capability_decision,
    create_chat_message,
    create_lifecycle_event,
)
from aura_cli.core.events.contracts import (
    CapabilityDecisionPayload,
    ChatMessagePayload,
    CheckpointPayload,
    LifecyclePayload,
    PlanningPayload,
    SubtaskPayload,
    TaskCompletePayload,
    TaskStartPayload,
    TaskUpdatePayload,
    ThinkingPayload,
    ToolExecutingPayload,
    ToolResultPayload,
    get_payload_schema,
    is_valid_event,
    validate_event,
)
from aura_cli.core.events.event_bus import (
    CoreEventBus,
    get_event_bus,
    get_status_queue,
    publish_event,
    subscribe_event,
)
from aura_cli.core.events.human_intervention_events import (
    RISK_CONFIG,
    InterventionContext,
    InterventionEventType,
    InterventionRequest,
    InterventionRequestType,
    InterventionResponse,
    RiskLevel,
    create_confirmation_request,
    create_input_request,
    create_manual_step_request,
    create_password_request,
    create_response,
    create_selection_request,
)

__all__ = [
    "RISK_CONFIG",
    "AgiEvent",
    "AgiEventType",
    "AgiTaskCompleteEvent",
    "AgiTaskStartEvent",
    "AgiTaskUpdateEvent",
    "CapabilityDecisionEvent",
    "CapabilityDecisionPayload",
    "ChatMessageEvent",
    "ChatMessagePayload",
    "CheckpointPayload",
    "CoreEventBus",
    "InterventionContext",
    "InterventionEventType",
    "InterventionRequest",
    "InterventionRequestType",
    "InterventionResponse",
    "LifecycleEvent",
    "LifecyclePayload",
    "PlanningPayload",
    "RiskLevel",
    "SubtaskPayload",
    "TaskCompletePayload",
    # Unified contracts
    "TaskStartPayload",
    "TaskUpdatePayload",
    "ThinkingPayload",
    "ToolExecutingEvent",
    "ToolExecutingPayload",
    "ToolResultEvent",
    "ToolResultPayload",
    "create_capability_decision",
    "create_chat_message",
    "create_confirmation_request",
    "create_input_request",
    "create_lifecycle_event",
    "create_manual_step_request",
    "create_password_request",
    "create_response",
    "create_selection_request",
    "get_event_bus",
    "get_payload_schema",
    "get_status_queue",
    "is_valid_event",
    "publish_event",
    "subscribe_event",
    "validate_event",
]
