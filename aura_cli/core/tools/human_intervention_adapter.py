"""Adapter to simplify human intervention requests in workers.

Provides simple interface for OpsWorker and AgiWorker to request
human intervention during execution.

Features:
    - Confirmation requests with timeout
    - Text input requests with validation
    - Password input (masked)
    - Selection from options
    - Manual step execution
    - Request-response lifecycle management

Architecture:
    Manages complete request-response cycle including timeouts and
    error handling. Uses event-based communication with UI layer.
"""

from queue import Queue
from threading import Event, Lock
import time
from typing import Any, Callable, Dict, List, Optional

from aura_cli.application.presentation.safe_payloads import safe_tool_args_json
from aura_cli.core.events.human_intervention_events import (
    InterventionContext,
    RiskLevel,
    create_confirmation_request,
    create_input_request,
    create_manual_step_request,
    create_password_request,
    create_selection_request,
)
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

# Registry so the UI layer can deliver responses to the correct worker adapter
_adapters_by_task: Dict[str, "HumanInterventionAdapter"] = {}
_adapters_lock = Lock()
_local_confirmation_handler: Optional[Callable[..., bool]] = None


def configure_local_confirmation_handler(
    handler: Optional[Callable[..., bool]],
) -> None:
    """Install the interactive confirmation adapter used by local CLI calls."""
    global _local_confirmation_handler
    _local_confirmation_handler = handler


def request_local_confirmation(
    message: str,
    *,
    default: bool = True,
    context: Optional[str] = None,
    timeout: Optional[float] = None,
) -> bool:
    """Request confirmation without importing a presentation implementation."""
    if _local_confirmation_handler is None:
        return default
    return _local_confirmation_handler(
        message,
        default=default,
        context=context,
        timeout=timeout,
    )


def register_intervention_adapter(
    task_id: str, adapter: "HumanInterventionAdapter"
) -> None:
    """Register adapter for a task so the UI can deliver intervention responses."""
    with _adapters_lock:
        _adapters_by_task[task_id] = adapter
    logger.debug("Intervention adapter registered for task %s", task_id)


def get_intervention_adapter(task_id: str) -> Optional["HumanInterventionAdapter"]:
    """Return the intervention adapter for the given task_id, or None."""
    with _adapters_lock:
        return _adapters_by_task.get(task_id)


def unregister_intervention_adapter(task_id: str) -> None:
    """Unregister adapter when the task finishes."""
    with _adapters_lock:
        _adapters_by_task.pop(task_id, None)
    logger.debug("Intervention adapter unregistered for task %s", task_id)


class HumanInterventionAdapter:
    """Adapter to simplify human intervention requests.

    Manages complete request-response cycle including timeouts
    and error handling.

    Attributes:
        status_queue: Queue for UI communication
        task_id: Current task ID
        default_timeout: Default timeout in seconds
        pending_requests: Dict of pending request events
        responses: Dict of received responses
    """

    def __init__(
        self,
        status_queue: Queue,
        task_id: str,
        default_timeout: int = 60,
        lifecycle_emitter: Any = None,
    ):
        """Initialize adapter.

        Args:
            status_queue: Queue for UI communication
            task_id: Current task ID
            default_timeout: Default timeout in seconds
        """
        self.status_queue = status_queue
        self.task_id = task_id
        self.default_timeout = default_timeout
        self.pending_requests: Dict[str, Event] = {}
        self.responses: Dict[str, Dict[str, Any]] = {}
        self._requests_lock = Lock()
        self.lifecycle_emitter = lifecycle_emitter

        logger.debug(f"HumanInterventionAdapter initialized for task {task_id}")

    def request_confirmation(
        self,
        prompt: str,
        context: Optional[InterventionContext] = None,
        default: bool = False,
        timeout: Optional[int] = None,
    ) -> bool:
        """Request user confirmation.

        Args:
            prompt: Question for user
            context: Operation context
            default: Default value
            timeout: Timeout in seconds

        Returns:
            True if approved, False otherwise
        """
        request_dict = create_confirmation_request(
            task_id=self.task_id,
            prompt=prompt,
            context=context,
            default=default,
            timeout=timeout or self.default_timeout,
        )

        response = self._send_and_wait(request_dict)
        return response.get("approved", False)

    def request_input(
        self,
        prompt: str,
        placeholder: Optional[str] = None,
        default: Optional[str] = None,
        multiline: bool = False,
        validator: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> Optional[str]:
        """Request free-text input from the user."""
        request_dict = create_input_request(
            task_id=self.task_id,
            prompt=prompt,
            placeholder=placeholder,
            default=default,
            multiline=multiline,
            validator=validator,
            timeout=timeout or self.default_timeout,
        )

        response = self._send_and_wait(request_dict)

        if response.get("approved"):
            return response.get("value")
        return None

    def request_password(
        self, prompt: str, timeout: Optional[int] = None
    ) -> Optional[str]:
        """Request a password from the user."""
        request_dict = create_password_request(
            task_id=self.task_id,
            prompt=prompt,
            timeout=timeout or self.default_timeout * 2,  # Dobro do timeout para senhas
        )

        response = self._send_and_wait(request_dict)

        if response.get("approved"):
            return response.get("value")
        return None

    def request_selection(
        self,
        prompt: str,
        options: List[str],
        multiple: bool = False,
        default: Optional[Any] = None,
        timeout: Optional[int] = None,
    ) -> Optional[Any]:
        """Request a selection from a list of options."""
        request_dict = create_selection_request(
            task_id=self.task_id,
            prompt=prompt,
            options=options,
            multiple=multiple,
            default=default,
            timeout=timeout or self.default_timeout,
        )

        response = self._send_and_wait(request_dict)

        if response.get("approved"):
            return response.get("value")
        return None

    def request_manual_step(
        self, prompt: str, instructions: List[str], timeout: Optional[int] = None
    ) -> bool:
        """Request the user to perform a manual step."""
        request_dict = create_manual_step_request(
            task_id=self.task_id,
            prompt=prompt,
            instructions=instructions,
            timeout=timeout or 300,  # 5 min default for manual steps
        )

        response = self._send_and_wait(request_dict)
        return response.get("approved", False)

    def _send_and_wait(
        self, request_dict: Dict[str, Any], poll_interval: float = 0.1
    ) -> Dict[str, Any]:
        """Send an intervention request and wait for response."""
        request_id = request_dict["request_id"]
        timeout = request_dict.get("timeout", self.default_timeout)

        response_event = Event()
        with self._requests_lock:
            self.pending_requests[request_id] = response_event

        logger.info(f"Enviando requisição de intervenção: {request_id}")
        if self.lifecycle_emitter is not None:
            context = request_dict.get("context") or {}
            metadata = context.get("metadata") or {}
            self.lifecycle_emitter.request_approval(
                request_id,
                str(request_dict.get("prompt") or "Human input required"),
                action=str(
                    context.get("tool_name")
                    or request_dict.get("request_type")
                    or "input"
                ),
                policy_key=(
                    str(metadata.get("policy_key"))
                    if metadata.get("policy_key")
                    else None
                ),
            )
        self.status_queue.put(request_dict)

        start_time = time.time()

        while True:
            if timeout:
                elapsed = time.time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Timeout na requisição {request_id}")
                    with self._requests_lock:
                        self.pending_requests.pop(request_id, None)
                        self.responses.pop(request_id, None)
                    if self.lifecycle_emitter is not None:
                        self.lifecycle_emitter.resolve_approval(
                            request_id,
                            approved=False,
                            message="Approval timed out",
                        )
                    return {"approved": False, "cancelled": True, "reason": "timeout"}

            with self._requests_lock:
                response = self.responses.pop(request_id, None)
                if response is not None:
                    self.pending_requests.pop(request_id, None)
            if response is not None:
                logger.info(
                    f"Resposta recebida para {request_id}: approved={response.get('approved')}"
                )
                if self.lifecycle_emitter is not None:
                    self.lifecycle_emitter.resolve_approval(
                        request_id,
                        approved=bool(response.get("approved")),
                        message="Approval resolved",
                        scope=str(response.get("scope") or "once"),
                    )
                return response

            response_event.wait(poll_interval)

    def receive_response(self, response_dict: Dict[str, Any]):
        """Receive and process an intervention response."""
        if not isinstance(response_dict, dict):
            logger.warning("Resposta de intervenção não é um dicionário; ignorada")
            return

        request_id = response_dict.get("request_id")
        task_id = response_dict.get("task_id")

        if not request_id:
            logger.warning("Resposta sem request_id recebida")
            return
        if task_id is not None and str(task_id) != self.task_id:
            logger.warning("Resposta descartada por task_id incompatível: %s", task_id)
            return

        with self._requests_lock:
            response_event = self.pending_requests.get(request_id)
            if response_event is None:
                logger.warning("Resposta órfã ou tardia descartada: %s", request_id)
                return
            self.responses[request_id] = response_dict
            response_event.set()

    def cancel_all_pending(self):
        """Cancel all pending intervention requests."""
        with self._requests_lock:
            pending = list(self.pending_requests.items())
            for request_id, response_event in pending:
                self.responses[request_id] = {
                    "task_id": self.task_id,
                    "request_id": request_id,
                    "approved": False,
                    "cancelled": True,
                    "reason": "worker_cancelled",
                }
                response_event.set()
            self.pending_requests.clear()
        logger.info(
            f"Todas as requisições pendentes canceladas para task {self.task_id}"
        )


class InterventionHelper:
    """Helper for managing human intervention requests."""

    @staticmethod
    def should_confirm_tool(
        tool_name: str, args: Dict[str, Any]
    ) -> Optional[RiskLevel]:
        """Return True if this tool call requires user confirmation."""
        CRITICAL_TOOLS: Dict[str, Dict[str, Any]] = {
            "run_shell_command": {
                "patterns": ["rm -r", "dd if=", "mkfs", "format"],
                "risk": RiskLevel.CRITICAL,
                "default_risk": RiskLevel.MEDIUM,  # any command requires confirmation
            },
            "git_push": {"patterns": ["--force", "-f"], "risk": RiskLevel.HIGH},
            "docker_rm": {"patterns": ["--force", "-f"], "risk": RiskLevel.HIGH},
            "write_file": {
                "patterns": ["/etc/", "/sys/", "/proc/", "/root/"],
                "risk": RiskLevel.HIGH,
            },
            "delete_file": {"patterns": [], "risk": RiskLevel.MEDIUM},
        }

        if tool_name not in CRITICAL_TOOLS:
            return None

        config = CRITICAL_TOOLS[tool_name]

        if not config["patterns"]:
            return config["risk"]

        args_str = str(args).lower()
        for pattern in config["patterns"]:
            if pattern.lower() in args_str:
                return config["risk"]

        # run_shell_command: any non-empty command requires at least default_risk confirmation
        if tool_name == "run_shell_command" and config.get("default_risk"):
            cmd = (args or {}).get("command") or (args or {}).get("cmd") or ""
            if isinstance(cmd, str) and cmd.strip():
                return config["default_risk"]
        return None

    @staticmethod
    def build_tool_confirmation_request(
        tool_name: str, args: Dict[str, Any]
    ) -> Optional[tuple[RiskLevel, InterventionContext, str, int]]:
        """
        Build the normalized confirmation request payload for a tool call.

        Returns:
            Tuple of (risk_level, context, prompt, timeout_seconds) or None
            when the tool does not require confirmation.
        """
        risk_level = InterventionHelper.should_confirm_tool(tool_name, args)
        if risk_level is None:
            return None

        context = InterventionHelper.create_tool_confirmation_context(
            tool_name=tool_name,
            args=args,
            risk_level=risk_level,
        )

        if risk_level == RiskLevel.CRITICAL:
            prompt = (
                f"▲ OPERAÇÃO CRÍTICA: {tool_name}\n"
                "Deseja realmente executar esta operação de alto risco?"
            )
            timeout = 120
        elif risk_level == RiskLevel.HIGH:
            prompt = f"🔶 Operação de alto impacto: {tool_name}\nConfirma a execução?"
            timeout = 60
        else:
            prompt = f"Confirma execução de {tool_name}?"
            timeout = 60

        return risk_level, context, prompt, timeout

    @staticmethod
    def create_tool_confirmation_context(
        tool_name: str, args: Dict[str, Any], risk_level: RiskLevel
    ) -> InterventionContext:
        """Create a confirmation context for a tool call."""
        return InterventionContext(
            tool_name=tool_name,
            tool_args=args,
            risk_level=risk_level,
            description="Esta operação pode ter impacto significativo no sistema.",
        )


def confirm_tool_execution_locally(
    tool_name: str,
    tool_args: Dict[str, Any],
    *,
    fallback_message: str,
    fallback_context: Optional[str] = None,
    console: Any = None,
    default: bool = False,
    force_auto_confirm: bool = False,
    auto_confirm_message: Optional[str] = None,
) -> bool:
    """
    Shared local confirmation path for tools executed outside the main handler.

    This preserves direct-tool guardrails while reusing the same risk
    classification and confirmation payload builder used by chat and AGI.
    """
    from aura_cli.application.tools.execution_policy import get_execution_policy
    from aura_cli.core.stats import get_stats

    stats = get_stats()
    if force_auto_confirm or stats.skip_confirmations:
        if auto_confirm_message and console is not None:
            console.print(auto_confirm_message)
        return True

    policy = get_execution_policy()
    confirmation_request = InterventionHelper.build_tool_confirmation_request(
        tool_name,
        tool_args,
    )

    if confirmation_request is None:
        message = fallback_message
        context = fallback_context
        timeout = 60
    else:
        risk_level, request_context, message, timeout = confirmation_request
        context = fallback_context
        if context is None and request_context.tool_args:
            context = safe_tool_args_json(request_context.tool_args)

        if policy is not None:
            risk_value = getattr(risk_level, "value", risk_level)
            risk_name = str(risk_value).casefold()
            if risk_name in {"high", "critical"} and not policy.allow_dangerous:
                return False
            if policy.auto_confirm and not policy.confirm_writes:
                if auto_confirm_message and console is not None:
                    console.print(auto_confirm_message)
                return True

    return request_local_confirmation(
        message,
        default=default,
        context=context,
        timeout=timeout,
    )
