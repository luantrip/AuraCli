"""Background AGI worker thread for autonomous project-manager tasks."""

import os
from pathlib import Path
import queue
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    pass

from aura_cli.application.agents.event_emitter import AgiEventAdapter
from aura_cli.application.agents.worker_lifecycle import (
    build_worker_error_payload,
    build_worker_success_payload,
    get_worker_failure_supervisor_state,
    summarize_worker_success,
)
from aura_cli.application.workspace import MemorySynchronizer
from aura_cli.cli.ui.components.subagent_panel import SubAgentPanel
from aura_cli.cli.ui.composition import publish_agent_status, publish_subagent_panel
from aura_cli.cli.ui.constants import UIIcons
from aura_cli.cli.workers.advanced_runtime import initialize_advanced_worker_runtime
from aura_cli.cli.workers.base_worker import BaseWorker
from aura_cli.cli.workers.tool_panel_helper import tool_panel_context
from aura_cli.core.agents.fallbacks import classify_fallback_reason
from aura_cli.core.agi.context import AgiContextManager
from aura_cli.core.agi.execution import AgiExecutionEngine
from aura_cli.core.agi.factory import AgiAgentFactory
from aura_cli.core.agi.planning import AgiPlanner
from aura_cli.core.agi.validation import AgiValidator
from aura_cli.core.constants import COMPRESSION_THRESHOLD, MAX_HISTORY_SIZE
from aura_cli.core.context.base import ContextManager
from aura_cli.core.git_manager import GitManager
from aura_cli.core.linter_manager import LinterManager
from aura_cli.core.logger import get_logger
from aura_cli.core.memory.constitution_validator import ConstitutionValidator
from aura_cli.core.memory.memory_service import get_memory_service
from aura_cli.core.memory.notebook_service import get_notebook_service
from aura_cli.core.paths import ArtifactLayout
from aura_cli.core.sessions.session_state import get_session_state
from aura_cli.core.tools.human_intervention_adapter import (
    HumanInterventionAdapter,
    register_intervention_adapter,
)

USE_ADK_BRIDGE = os.getenv("AURA_USE_ADK_BRIDGE", "true").lower() == "true"


def _use_adk_bridge_enabled() -> bool:
    """Read the feature flag when constructing the AGI runtime."""
    from aura_cli.core.agents import is_adk_bridge_enabled

    return is_adk_bridge_enabled()


try:
    from aura_cli.core.personas.integrations import get_consciousness_manager

    CONSCIOUSNESS_AVAILABLE = True
except ImportError:
    CONSCIOUSNESS_AVAILABLE = False
try:
    from aura_cli.core.tools.imagination_tools import get_imagination_scanner

    IMAGINATION_AVAILABLE = True
except ImportError:
    IMAGINATION_AVAILABLE = False

logger = get_logger(__name__)


try:
    from aura_cli.cli.ui import loading_states as _loading_states

    LOADING_AVAILABLE = _loading_states is not None
except ImportError:
    LOADING_AVAILABLE = False
    logger.debug("Loading states não disponível em AgiWorker")

try:
    from aura_cli.cli.workers.tester_worker import TesterWorker

    TESTER_WORKER_AVAILABLE = True
except ImportError:
    TESTER_WORKER_AVAILABLE = False
    TesterWorker = None  # type: ignore[assignment,misc]
    logger.debug("TesterWorker não disponível em AgiWorker")


class AgiWorker(BaseWorker):
    """Background worker for AGI analysis with access to the full tool catalogue."""

    max_execution_time: float = 600.0  # 10 minutes for AGI tasks
    dashboard_prefix = "Aura AGI"

    def __init__(
        self,
        prompt: str,
        model: str,
        api_keys: dict,
        headless: bool = False,
        status_queue: Optional[queue.Queue[Any]] = None,
        available_tools: Optional[Dict[str, Any]] = None,
        use_advanced_features: bool = True,
        task_id: str = "global_agi_task",
        enable_adversarial_validation: bool = False,
        project_root: Optional[Path] = None,
        constitution: Optional[str] = None,
        delegation_payload: Optional[Dict[str, Any]] = None,
    ):
        """Initialise the AGI worker."""
        super().__init__(
            status_queue=status_queue,
            task_id=task_id,
            headless=headless,
        )
        self.prompt = prompt
        self.model = model
        self.api_keys = api_keys
        self.context_manager = ContextManager(
            max_history_size=MAX_HISTORY_SIZE,
            compression_threshold=COMPRESSION_THRESHOLD,
        )
        self.available_tools = available_tools or {}
        self.use_advanced_features = use_advanced_features
        self.enable_adversarial_validation = enable_adversarial_validation
        self.generated_files: List[str] = []  # Track files for adversarial validation
        self.edited_files: List[str] = []
        self.analyzed_files: List[str] = []
        self.delegation_payload = delegation_payload or {}

        self.agi_event_adapter = AgiEventAdapter(self.status_queue, self.task_id)

        self.human_intervention_adapter = HumanInterventionAdapter(
            status_queue=self.status_queue,
            task_id=self.task_id,
            default_timeout=60,
            lifecycle_emitter=self.agi_event_adapter,
        )
        register_intervention_adapter(self.task_id, self.human_intervention_adapter)

        self.orchestrator = None
        self.communication_manager = None
        self.workflow_executor = None
        if self.use_advanced_features:
            from aura_cli.core.agents.planning.problem_decomposer import (
                ProblemDecomposer,
            )
            from aura_cli.core.agents.planning.task_planner import TaskPlanner

            self.task_planner = TaskPlanner()
            self.problem_decomposer = ProblemDecomposer()
        else:
            self.task_planner = None  # type: ignore[assignment]
            self.problem_decomposer = None  # type: ignore[assignment]
        self.agent_memory = None
        self.planner = None  # initialized in _initialize_advanced_components
        self.context_manager_service = None
        self.consciousness_manager = None
        if CONSCIOUSNESS_AVAILABLE:
            try:
                self.consciousness_manager = get_consciousness_manager()
                logger.info("ConsciousnessManager initialized for AgiWorker")
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to initialize ConsciousnessManager: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error initializing ConsciousnessManager: {e}",
                    exc_info=True,
                )
        self.imagination_scanner = None
        self.project_context = None
        if IMAGINATION_AVAILABLE:
            try:
                self.imagination_scanner = get_imagination_scanner()
                logger.info("ImaginationScanner initialized for AgiWorker")
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to initialize ImaginationScanner: {e}")
            except Exception as e:
                logger.error(
                    f"Unexpected error initializing ImaginationScanner: {e}",
                    exc_info=True,
                )

        self.project_root = project_root or Path.cwd()
        self.constitution = constitution

        self._memory_service = get_memory_service(self.project_root)
        self._session_state = get_session_state()
        self._notebook_service = get_notebook_service(
            base_path=ArtifactLayout(self.project_root).project("notebooks")
        )
        self._last_notebook_snapshot = 0
        self._notebook_snapshot_interval = (
            COMPRESSION_THRESHOLD  # Snapshot a cada N mensagens
        )

        if self.constitution is None:
            try:
                session = self._session_state.get_current_state()
                if session and session.constitution:
                    self.constitution = session.constitution
                    logger.info("Constitution loaded from session state cache")
                else:
                    self.constitution = self._memory_service.get_constitution()
                    if self.constitution:
                        logger.info(
                            "Constituição carregada do serviço de memória unificado"
                        )

                if self.constitution and not self.headless:
                    self.agi_event_adapter.emit_chat_message(
                        sender="system",
                        content=f"› [Aura AGI] {UIIcons.INFO} Constituição do Projeto carregada e ativa",
                    )
            except (OSError, KeyError) as e:
                logger.debug(
                    f"Não foi possível carregar a constituição para AgiWorker: {e}"
                )
                self.constitution = None
            except Exception as e:
                logger.warning(
                    f"Erro inesperado ao carregar constituição: {e}", exc_info=True
                )
                self.constitution = None

        session = self._session_state.get_current_state()
        if session and session.constitution_validator:
            self.constitution_validator = session.constitution_validator
        else:
            self.constitution_validator = ConstitutionValidator(self.constitution)

        self.linter_manager = LinterManager(self.project_root)

        self.learned_rules: List[Dict[str, str]] = []
        self.final_result: Optional[Dict[str, Any]] = None
        self.final_error: Optional[Dict[str, Any]] = None
        self.last_snapshot_path: Optional[str] = None
        self.completed_at: Optional[float] = None

        self.git_manager = GitManager(self.project_root)

    def _record_final_result(self, result: Dict[str, Any]) -> None:
        """Persist final successful worker result for follow-up/reconciliation."""
        self.completed_at = time.time()
        payload = build_worker_success_payload(
            result,
            task_id=self.task_id,
            completed_at=self.completed_at,
            delegation_payload=self.delegation_payload,
            snapshot_path=self.last_snapshot_path,
        )
        published = self._publish_terminal_result(payload)
        self.final_result = published
        self.final_error = None
        if hasattr(self, "agi_event_adapter") and self.agi_event_adapter:
            self.agi_event_adapter.complete_task(
                True,
                result=summarize_worker_success(published),
                stats={
                    "supervisor_state": "completed",
                    "fallback_reason": None,
                },
            )

    def _record_final_error(self, error: Any, *, error_code: str | None = None) -> None:
        """Persist final worker error for follow-up/reconciliation."""
        self.completed_at = time.time()
        fallback_reason = classify_fallback_reason(error)
        error_payload = build_worker_error_payload(
            error,
            task_id=self.task_id,
            prompt=self.prompt,
            completed_at=self.completed_at,
            fallback_reason=fallback_reason,
            delegation_payload=self.delegation_payload,
            snapshot_path=self.last_snapshot_path,
            error_code=error_code,
        )
        self.final_error = self._publish_terminal_result(error_payload)
        if hasattr(self, "agi_event_adapter") and self.agi_event_adapter:
            supervisor_state = get_worker_failure_supervisor_state(fallback_reason)
            self.agi_event_adapter.update_task(
                supervisor_state,
                "Worker returned control to chat",
                details={
                    "supervisor_state": supervisor_state,
                    "fallback_reason": fallback_reason,
                },
            )
            self.agi_event_adapter.error_task(
                error,
                details={
                    "supervisor_state": supervisor_state,
                    "fallback_reason": fallback_reason,
                },
            )

    def _initialize_advanced_components(self) -> None:
        """Initialise advanced components (orchestrator, communication, etc.)."""
        if self.orchestrator and self.task_planner:
            return

        try:
            self.planner = AgiPlanner(  # type: ignore[assignment]
                model=self.model,
                project_root=self.project_root,
                agi_event_adapter=self.agi_event_adapter,
                human_intervention_adapter=self.human_intervention_adapter,
                task_planner=self.task_planner,
                problem_decomposer=self.problem_decomposer,
                use_advanced_features=self.use_advanced_features,
            )

            self.context_manager_service = AgiContextManager(  # type: ignore[assignment]
                project_root=self.project_root,
                constitution=self.constitution,
                agi_event_adapter=self.agi_event_adapter,
                imagination_scanner=self.imagination_scanner,
                consciousness_manager=getattr(self, "consciousness_manager", None),
            )

            self.validator = AgiValidator(
                constitution=self.constitution,
                agi_event_adapter=self.agi_event_adapter,
                linter_manager=self.linter_manager,
                memory_service=self._memory_service
                if hasattr(self, "_memory_service")
                else None,
                session_state=self._session_state
                if hasattr(self, "_session_state")
                else None,
                tester_worker_class=TesterWorker if TESTER_WORKER_AVAILABLE else None,
                headless=self.headless,
            )

            runtime = initialize_advanced_worker_runtime(
                channel_id="main_channel",
                channel_name="Canal Principal",
                memory_storage_path=str(
                    ArtifactLayout(self.project_root).project("agent_memory")
                ),
                orchestrator=self.orchestrator,
                communication_manager=self.communication_manager,
                workflow_executor=self.workflow_executor,
                agent_memory=self.agent_memory,
            )
            self.orchestrator = runtime.orchestrator
            self.communication_manager = runtime.communication_manager
            self.workflow_executor = runtime.workflow_executor
            self.agent_memory = runtime.agent_memory

            if hasattr(self.orchestrator, "context") and self.orchestrator.context:  # type: ignore
                assert self.orchestrator is not None
                self.orchestrator.context.shared_memory["agent_memory_service"] = (
                    self.agent_memory
                )
                self.orchestrator.context.shared_memory["communication_manager"] = (
                    self.communication_manager
                )

            self.factory = AgiAgentFactory(
                orchestrator=self.orchestrator,
                communication_manager=self.communication_manager,
                agi_event_adapter=self.agi_event_adapter,
                consciousness_manager=self.consciousness_manager
                if hasattr(self, "consciousness_manager")
                else None,
                model=self.model,
                agent_memory=self.agent_memory,
                use_adk=_use_adk_bridge_enabled(),
                memory_synchronizer=MemorySynchronizer(),
            )

            self.engine = AgiExecutionEngine(
                agi_worker=self,
                planner=self.planner,
                context_manager=self.context_manager_service,
                validator=self.validator,
                workflow_executor=self.workflow_executor,
                orchestrator=self.orchestrator,
                git_manager=self.git_manager,
                communication_manager=self.communication_manager,
                agent_memory=self.agent_memory,
                progress_factory=lambda title: SubAgentPanel(title=title),
                publish_progress=publish_subagent_panel,
                publish_status=publish_agent_status,
                tool_panel_context_factory=tool_panel_context,
            )

            self.factory.create_specialized_agents(self.prompt)

            logger.info("Advanced AGI components initialized successfully")

        except (ImportError, AttributeError, TypeError) as e:
            logger.error(
                f"Error initializing advanced components (import/type): {e}",
                exc_info=True,
            )
        except Exception as e:
            logger.error(
                f"Unexpected error initializing advanced components: {e}", exc_info=True
            )
            self.agi_event_adapter.emit_chat_message(
                sender="agent",
                content=f"› [Aura AGI] {UIIcons.WARNING} Some advanced components could not be initialized",
            )
            self.use_advanced_features = False

    def _handle_run_exception(self, error: Exception) -> None:
        """Translate an unhandled AGI execution failure."""
        self._record_final_error(error)
        logger.critical(f"AgiWorker thread crashed: {error}", exc_info=True)
        self._publish_terminal_result(
            self.final_error
            or {
                "status": "error",
                "error": str(error),
                "error_code": "worker_error",
                "prompt": self.prompt,
                "delegation_payload": self.delegation_payload,
            }
        )
        if hasattr(self, "agi_event_adapter") and self.agi_event_adapter:
            try:
                self.agi_event_adapter.emit_chat_message(
                    sender="system",
                    content=f"› [Aura AGI] ❌ Erro crítico no worker: {error}",
                )
            except Exception as emit_error:
                logger.debug(f"Failed to emit error event: {emit_error}")
        try:
            self.cleanup()
        except Exception as cleanup_error:
            logger.warning(f"Falha no cleanup do AGI worker: {cleanup_error}")

    def _run_impl(self) -> None:
        """Execute the AGI analysis in the background."""
        # Autonomous confirmation is scoped to this worker's task policy.
        loading = None
        # Loading spinner is initialized later via LOADING_AVAILABLE guard when needed

        self.agi_event_adapter.emit_chat_message(
            sender="agent",
            content=f"› [Aura AGI] {UIIcons.THINKING} Iniciando análise de contexto...",
        )

        if self.use_advanced_features:
            self._initialize_advanced_components()
            if not self.headless:
                self._start_dashboard()

        if hasattr(self, "engine"):
            self.engine.run(self.prompt, loading)
        else:
            logger.error("AgiExecutionEngine not initialized!")
            self.agi_event_adapter.emit_chat_message(
                sender="system",
                content=f"› [Aura AGI] {UIIcons.ERROR} Falha crítica: Engine não inicializada.",
            )
            self._record_final_error(
                "AgiExecutionEngine not initialized",
                error_code="dependency",
            )
            self._publish_terminal_result(
                {
                    "status": "error",
                    "error": "AgiExecutionEngine not initialized",
                    "error_code": "dependency",
                    "prompt": self.prompt,
                    "delegation_payload": self.delegation_payload,
                }
            )

    def _save_worker_snapshot(self) -> None:
        """Save an execution snapshot to the Notebook."""
        try:
            page_path = self._create_notebook_snapshot()
            if page_path is None:
                return

            logger.info(f"Snapshot AGI salvo no Notebook: {page_path}")

            if not self.headless:
                self.agi_event_adapter.emit_chat_message(
                    sender="system",
                    content=f"› [Aura AGI] {UIIcons.SUCCESS} Análise salva no caderno: {Path(page_path).name}",
                )
        except Exception as e:
            logger.warning(f"Error saving AGI snapshot: {e}")
