"""Abstract base class for all Aura CLI agents.

AgentBase defines the common interface (execute_task, state management,
LLM communication, tool access, logging). AgentTask is the task contract;
AgentStatus tracks idle/thinking/working/error states. All specialized
agents inherit from this class.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import threading
from typing import Any, Dict, List, Optional

from rich.console import Console

from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


class AgentStatus(Enum):
    """Agent status enum."""

    IDLE = "idle"
    THINKING = "thinking"
    WORKING = "working"
    WAITING = "waiting"
    ERROR = "error"
    COMPLETED = "completed"


@dataclass
class AgentTask:
    """Represents a task for an agent (id, description, parameters, priority)."""

    id: str
    description: str
    priority: int = 5
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    status: AgentStatus = AgentStatus.IDLE


@dataclass
class AgentContext:
    """Shared context between agents (conversation_history, codebase_context, etc.)."""

    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    codebase_context: Dict[str, Any] = field(default_factory=dict)
    tool_results: Dict[str, Any] = field(default_factory=dict)
    shared_memory: Dict[str, Any] = field(default_factory=dict)


class AgentBase(ABC):
    """Abstract base class for all agents. Defines task-execution interface."""

    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        model: Optional[str] = None,
        context: Optional[AgentContext] = None,
    ):
        """Initialise the agent with an execution context."""
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.model = model
        self.context = context or AgentContext()

        self.status = AgentStatus.IDLE
        self.current_task: Optional[AgentTask] = None
        self.task_queue: List[AgentTask] = []
        self.completed_tasks: List[AgentTask] = []
        self._task_queue_lock = threading.RLock()

        self.stats = get_stats()
        self.tasks_executed = 0
        self.tools_used = 0
        self.errors_count = 0

        # Consciousness integration - can be set by AgiWorker
        self.consciousness_persona: Optional[Dict[str, Any]] = None
        self.consciousness_skills: Optional[List[Dict[str, Any]]] = None

        logger.info(f"Agent '{self.name}' ({self.agent_id}) initialized")

    @abstractmethod
    def _execute_task(self, task: AgentTask) -> Any:
        """Execute a specific task. Abstract — must be implemented by subclasses."""

    @abstractmethod
    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """Return available tools as a dict."""

    def _validate_task(self, task: AgentTask) -> bool:
        """Return True if the task is valid and executable."""
        for dep_id in task.dependencies:
            dep_completed = any(
                t.id == dep_id and t.status == AgentStatus.COMPLETED
                for t in self.completed_tasks
            )
            if not dep_completed:
                logger.warning(
                    f"Task {task.id} cannot be executed: "
                    f"dependency {dep_id} not completed"
                )
                return False

        if task.status == AgentStatus.ERROR:
            logger.warning(f"Task {task.id} is in error state")
            return False

        return True

    def add_task(
        self,
        description: str,
        priority: int = 5,
        dependencies: Optional[List[str]] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Add a task to the execution queue."""
        import uuid

        task_id = str(uuid.uuid4())[:8]

        task = AgentTask(
            id=task_id,
            description=description,
            priority=priority,
            dependencies=dependencies or [],
            parameters=parameters or {},
        )

        with self._task_queue_lock:
            self.task_queue.append(task)
            self.task_queue.sort(key=lambda t: t.priority, reverse=True)

        logger.info(f"Task {task_id} added to agent {self.name}: {description}")

        return task_id

    def execute_next_task(self) -> Optional[Any]:
        """Execute the next task in the queue and return its result."""
        with self._task_queue_lock:
            next_task = None
            for task in self.task_queue:
                if self._validate_task(task):
                    next_task = task
                    break

            if not next_task:
                if self.task_queue:
                    logger.info(
                        f"Agent {self.name}: No executable task available "
                        f"(pending dependencies)"
                    )
                return None

            self.task_queue.remove(next_task)
        self.current_task = next_task
        self.status = AgentStatus.WORKING
        next_task.status = AgentStatus.WORKING

        logger.info(
            f"Agent {self.name} executing task {next_task.id}: "
            f"{next_task.description}"
        )

        from aura_cli.core.ui import display_tool_call

        display_tool_call(
            f"agent_{self.agent_id}_execute",
            {
                "task_id": next_task.id,
                "description": next_task.description,
                "priority": next_task.priority,
            },
        )

        try:
            result = self._execute_task(next_task)

            next_task.result = result
            next_task.status = AgentStatus.COMPLETED
            self.completed_tasks.append(next_task)
            self.tasks_executed += 1
            self.stats.track_tool_usage(f"agent_{self.agent_id}")

            with self._task_queue_lock:
                if self.task_queue:
                    self.status = AgentStatus.IDLE
                else:
                    self.status = AgentStatus.COMPLETED

            self.current_task = None

            from aura_cli.core.ui_bridge import UIIcons, UIStyles

            success_style = UIStyles.safe_style("SUCCESS", "green")
            console.print(
                f"[{success_style}]{UIIcons.SUCCESS} "
                f"Task {next_task.id} completed by {self.name}[/{success_style}]"
            )

            logger.info(f"Task {next_task.id} completed successfully by {self.name}")

            return result

        except Exception as e:
            next_task.status = AgentStatus.ERROR
            next_task.result = {"error": str(e)}
            self.errors_count += 1
            self.status = AgentStatus.ERROR

            error_msg = (
                f"Error executing task {next_task.id} on agent {self.name}: {e}"
            )
            logger.error(error_msg, exc_info=True)

            from aura_cli.core.ui_bridge import UIIcons, UIStyles

            error_style = UIStyles.safe_style("ERROR", "red")
            console.print(f"[{error_style}]{UIIcons.ERROR} {error_msg}[/{error_style}]")

            raise

    def get_status(self) -> Dict[str, Any]:
        """Return agent status and metrics as a dict."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "current_task": self.current_task.id if self.current_task else None,
            "tasks_queued": len(self.task_queue),
            "tasks_completed": len(self.completed_tasks),
            "tasks_executed": self.tasks_executed,
            "tools_used": self.tools_used,
            "errors_count": self.errors_count,
        }

    def reset(self) -> None:
        """Reset agent state, task queue, completed tasks and statistics."""
        with self._task_queue_lock:
            self.task_queue.clear()
        self.completed_tasks.clear()
        self.current_task = None
        self.status = AgentStatus.IDLE
        self.tasks_executed = 0
        self.tools_used = 0
        self.errors_count = 0

        logger.info(f"Agent {self.name} reset")

    def get_consciousness_enhanced_prompt(self, base_prompt: str) -> str:
        """
        Build a prompt enhanced with consciousness data (persona and skills).

        This method integrates knowledge from the consciousness system
        into the agent's prompt, making it more context-aware.

        Args:
            base_prompt: The base system prompt

        Returns:
            Enhanced prompt with consciousness data
        """
        parts = [base_prompt]

        if self.consciousness_persona:
            persona_section = (
                f"\n\n## 🎭 Persona: {self.consciousness_persona.get('name', 'Specialist')}\n\n"
                f"{self.consciousness_persona.get('system_prompt', '')}"
            )
            parts.append(persona_section)

        if self.consciousness_skills:
            skills_content = []
            for skill in self.consciousness_skills:
                skill_text = (
                    f"### {skill.get('name', 'Unknown')}\n{skill.get('content', '')}"
                )
                skills_content.append(skill_text)

            if skills_content:
                skills_section = (
                    "\n\n## 📚 Conhecimento Relevante\n\n"
                    + "\n\n---\n\n".join(skills_content)
                )
                parts.append(skills_section)

        return "\n".join(parts)

    def has_consciousness(self) -> bool:
        """Check if agent has consciousness data loaded."""
        return bool(self.consciousness_persona or self.consciousness_skills)

    def __repr__(self) -> str:
        """Return a string representation of the agent."""
        return (
            f"<AgentBase(id={self.agent_id}, name={self.name}, "
            f"status={self.status.value})>"
        )
