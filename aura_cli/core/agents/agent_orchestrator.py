"""Multi-agent orchestrator for Aura CLI.

AgentOrchestrator registers specialized agents, distributes tasks based on
agent specialisation, and executes them in parallel or priority order with
configurable concurrency limits. Provides inter-agent context sharing and
per-agent metrics.
"""

from collections import defaultdict
from dataclasses import dataclass
import threading
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from aura_cli.core.agents.agent_base import AgentBase, AgentContext, AgentTask
from aura_cli.core.constants import MAX_AGENT_ITERATIONS
from aura_cli.core.logger import get_logger
from aura_cli.core.stats import get_stats

logger = get_logger(__name__)
console = Console()


@dataclass
class OrchestrationStrategy:
    """
    Agent orchestration strategy configuration.

    Attributes:
        parallel: If True, execute agents in parallel when possible
        max_concurrent: Maximum number of agents executing simultaneously
        priority_ordering: If True, order tasks by global priority
        load_balancing: If True, distribute tasks balancing load across agents
    """

    parallel: bool = True
    max_concurrent: int = 3
    priority_ordering: bool = True
    load_balancing: bool = True


class AgentOrchestrator:
    """
    Main orchestrator for managing multiple agents.

    Features:
    - Agent registration and management
    - Task distribution among agents
    - Parallel/sequential execution coordination
    - Inter-agent communication
    - Status and statistics monitoring
    """

    def __init__(
        self,
        context: Optional[AgentContext] = None,
        strategy: Optional[OrchestrationStrategy] = None,
    ):
        """
        Initialize the orchestrator.

        Args:
            context: Shared context between agents
            strategy: Orchestration strategy (None = default)
        """
        self.context = context or AgentContext()
        self.strategy = strategy or OrchestrationStrategy()

        self.agents: Dict[str, AgentBase] = {}
        self.agent_types: Dict[str, List[str]] = defaultdict(list)

        self.lock = threading.RLock()
        self.running = False

        self.stats = get_stats()
        self.total_tasks_distributed = 0
        self.total_tasks_completed = 0

        logger.info("AgentOrchestrator initialized")

    def register_agent(self, agent: AgentBase) -> None:
        """
        Register an agent with the orchestrator.

        Args:
            agent: Agent instance to register (must inherit from AgentBase)
        """
        try:
            if not isinstance(agent, AgentBase):
                agent_type = type(agent)
                agent_mro = agent_type.__mro__
                if "aura_cli.adk" in str(agent_type) or any(
                    "aura_cli.adk" in str(base) for base in agent_mro
                ):
                    # Auto-wrap ADK agents using ADKAgentWrapper
                    try:
                        from aura_cli.core.agents.adk_wrapper import ADKAgentWrapper

                        agent = ADKAgentWrapper(adk_agent=agent)
                        logger.info(
                            f"Auto-wrapped ADK agent {agent_type} as ADKAgentWrapper"
                        )
                    except Exception as wrap_err:
                        logger.error(
                            f"Failed to auto-wrap ADK agent {agent_type}: {wrap_err}"
                        )
                        raise TypeError(
                            f"Agent {agent_type} is an ADK agent that could not be auto-wrapped: {wrap_err}. "
                            f"Please disable USE_ADK_BRIDGE or use the native Core specialized agents."
                        ) from wrap_err
                else:
                    required_methods = ["add_task", "execute_next_task", "task_queue"]
                    missing_methods = [
                        m for m in required_methods if not hasattr(agent, m)
                    ]
                    if missing_methods:
                        logger.error(
                            f"Agent {agent_type} is not an AgentBase and is missing required methods: {missing_methods}"
                        )
                        raise TypeError(
                            f"Agent {agent_type} must inherit from AgentBase or have methods: {required_methods}. "
                            f"Missing: {missing_methods}"
                        )

            if not hasattr(agent, "agent_id") or agent.agent_id is None:
                if hasattr(agent, "config") and hasattr(agent.config, "name"):
                    agent.agent_id = agent.config.name
                elif hasattr(agent, "name"):
                    agent.agent_id = agent.name.lower().replace(" ", "_")
                else:
                    agent.agent_id = agent.__class__.__name__.lower()
                logger.debug(
                    f"Generated agent_id '{agent.agent_id}' for agent {agent.__class__.__name__}"
                )

            if not hasattr(agent, "name") or agent.name is None:
                if hasattr(agent, "config") and hasattr(agent.config, "name"):
                    agent.name = agent.config.name
                else:
                    agent.name = agent.__class__.__name__

            if agent.agent_id in self.agents:
                logger.warning(f"Agent {agent.agent_id} already registered, replacing")

            self.agents[agent.agent_id] = agent

            if hasattr(agent, "context"):
                try:
                    agent.context = self.context
                except Exception as e:
                    logger.warning(
                        f"Failed to set context for agent {agent.agent_id}: {e}"
                    )

            agent_type = agent.__class__.__name__
            self.agent_types[agent_type].append(agent.agent_id)

            logger.info(
                f"Agent {agent.name} ({agent.agent_id}) registered as {agent_type}"
            )

            from aura_cli.core.ui_bridge import UIIcons, UIStyles

            success_style = UIStyles.safe_style("SUCCESS", "green")
            console.print(
                f"[{success_style}]{UIIcons.SUCCESS} "
                f"Agent '{agent.name}' registered[/{success_style}]"
            )
        except Exception as e:
            logger.error(f"Failed to register agent: {e}", exc_info=True)
            raise

    def unregister_agent(self, agent_id: str) -> None:
        """
        Remove an agent from the orchestrator.

        Args:
            agent_id: ID of the agent to remove
        """
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} is not registered")
            return

        agent = self.agents[agent_id]
        agent_type = agent.__class__.__name__

        del self.agents[agent_id]
        if agent_id in self.agent_types[agent_type]:
            self.agent_types[agent_type].remove(agent_id)

        logger.info(f"Agent {agent_id} removed from orchestrator")

    def get_agent(self, agent_id: str) -> Optional[AgentBase]:
        """
        Get an agent by ID.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent instance or None if not found
        """
        return self.agents.get(agent_id)

    def get_agents_by_type(self, agent_type: str) -> List[AgentBase]:
        """
        Get all agents of a specific type.

        Args:
            agent_type: Agent class name

        Returns:
            List of agents of the specified type
        """
        agent_ids = self.agent_types.get(agent_type, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]

    def distribute_task(
        self,
        task_description: str,
        agent_id: Optional[str] = None,
        agent_type: Optional[str] = None,
        priority: int = 5,
        parameters: Optional[Dict[str, Any]] = None,
        use_strategy_card: bool = False,
    ) -> str:
        """
        Distribute a task to a specific agent or type.

        Args:
            task_description: Task description
            agent_id: Specific agent ID (None = auto-select)
            agent_type: Agent type (None = any)
            priority: Task priority
            parameters: Task parameters

        Returns:
            Created task ID

        Raises:
            ValueError: If no suitable agent is found
        """
        if agent_id:
            agent = self.get_agent(agent_id)
            if not agent:
                raise ValueError(f"Agent {agent_id} not found")
        elif agent_type:
            agents = self.get_agents_by_type(agent_type)
            if not agents:
                raise ValueError(f"No agents of type {agent_type} found")
            if self.strategy.load_balancing:
                agent = min(agents, key=lambda a: len(a.task_queue))
            else:
                agent = agents[0]
        else:
            if not self.agents:
                raise ValueError("No agents registered")
            agent = min(self.agents.values(), key=lambda a: len(a.task_queue))

        if not hasattr(agent, "add_task"):
            logger.error(
                f"Agent {agent.agent_id} ({agent.__class__.__name__}) does not have add_task method"
            )
            logger.error(f"Agent attributes: {dir(agent)}")
            logger.error(f"Agent type: {type(agent)}")
            logger.error(f"Agent MRO: {agent.__class__.__mro__}")
            raise AttributeError(
                f"Agent {agent.agent_id} ({agent.__class__.__name__}) does not have add_task method. "
                f"Agent may not be properly initialized. "
                f"Agent type: {type(agent)}, MRO: {agent.__class__.__mro__}"
            )

        if not hasattr(agent, "task_queue"):
            logger.error(
                f"Agent {agent.agent_id} ({agent.__class__.__name__}) does not have task_queue attribute"
            )
            raise AttributeError(
                f"Agent {agent.agent_id} ({agent.__class__.__name__}) is not properly initialized. "
                f"Missing task_queue attribute."
            )

        task_parameters = dict(parameters or {})
        if use_strategy_card:
            from aura_cli.core.agents.strategy_deck import StrategyDeck
            task_parameters["strategy_card"] = StrategyDeck().draw_one().to_dict()

        try:
            task_id = agent.add_task(
                description=task_description,
                priority=priority,
                parameters=task_parameters,
            )
        except AttributeError as e:
            logger.error(f"Error calling add_task on agent {agent.agent_id}: {e}")
            logger.error(
                f"Agent class: {agent.__class__}, Agent MRO: {agent.__class__.__mro__}"
            )
            raise

        self.total_tasks_distributed += 1
        self.stats.track_tool_usage("orchestrator_distribute_task")

        logger.info(
            f"Task {task_id} distributed to agent {agent.name} ({agent.agent_id})"
        )

        return task_id

    def execute_all_agents(
        self, max_iterations: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute all agents until no tasks remain.

        Args:
            max_iterations: Maximum iterations to prevent infinite loops.
                          If None, reads from user configuration (max_loops).

        Returns:
            Dictionary with results and statistics
        """
        if max_iterations is None:
            try:
                from aura_cli.core.config import get_config_manager

                config = get_config_manager()
                max_iterations = config.get("max_loops") or MAX_AGENT_ITERATIONS
            except Exception:
                max_iterations = MAX_AGENT_ITERATIONS
        from aura_cli.core.ui import display_tool_call

        display_tool_call(
            "orchestrator_execute_all",
            {
                "agents_count": len(self.agents),
                "max_iterations": max_iterations,
                "strategy": {
                    "parallel": self.strategy.parallel,
                    "max_concurrent": self.strategy.max_concurrent,
                },
            },
        )

        self.running = True
        iteration = 0
        results = {}

        logger.info(
            f"Starting execution of {len(self.agents)} agents "
            f"(strategy: {'parallel' if self.strategy.parallel else 'sequential'})"
        )

        try:
            while self.running and iteration < max_iterations:
                all_tasks = []
                for agent in self.agents.values():
                    if agent.task_queue:
                        all_tasks.append((agent, agent.task_queue[0]))

                if not all_tasks:
                    break

                if self.strategy.priority_ordering:
                    all_tasks.sort(key=lambda x: x[1].priority, reverse=True)

                if self.strategy.parallel:
                    with self.lock:
                        concurrent_tasks = all_tasks[: self.strategy.max_concurrent]
                        threads = []

                        for agent, task in concurrent_tasks:
                            thread = threading.Thread(
                                target=self._execute_agent_task,
                                args=(agent, task),
                                daemon=True,
                            )
                            thread.start()
                            threads.append(thread)

                    for thread in threads:
                        thread.join()
                else:
                    for agent, _ in all_tasks:
                        try:
                            agent.execute_next_task()
                            self.total_tasks_completed += 1
                        except Exception as e:
                            logger.error(
                                f"Error executing task on agent {agent.name}: {e}",
                                exc_info=True,
                            )

                iteration += 1

            for agent_id, agent in self.agents.items():
                results[agent_id] = {
                    "status": agent.get_status(),
                    "completed_tasks": [
                        {
                            "id": t.id,
                            "description": t.description,
                            "result": str(t.result)[:200] if t.result else None,
                        }
                        for t in agent.completed_tasks
                    ],
                }

            logger.info(
                f"Execution completed after {iteration} iterations. "
                f"{self.total_tasks_completed} tasks completed"
            )

        finally:
            self.running = False

        return {
            "iterations": iteration,
            "tasks_completed": self.total_tasks_completed,
            "agents_results": results,
        }

    def _execute_agent_task(self, agent: AgentBase, task: AgentTask) -> None:
        """
        Execute an agent task in a separate thread.

        Args:
            agent: Agent to execute
            task: Task to execute
        """
        try:
            with self.lock:
                if not self.running:
                    return

            result = agent.execute_next_task()

            if result is not None:
                with self.lock:
                    self.total_tasks_completed += 1

        except Exception as e:
            logger.error(
                f"Error executing task {task.id} on agent {agent.name}: {e}",
                exc_info=True,
            )

    def get_status(self) -> Dict[str, Any]:
        """
        Get complete orchestrator status.

        Returns:
            Dictionary with status of all agents
        """
        agents_status = {}
        for agent_id, agent in self.agents.items():
            agents_status[agent_id] = agent.get_status()

        return {
            "agents_count": len(self.agents),
            "running": self.running,
            "total_tasks_distributed": self.total_tasks_distributed,
            "total_tasks_completed": self.total_tasks_completed,
            "agents": agents_status,
            "strategy": {
                "parallel": self.strategy.parallel,
                "max_concurrent": self.strategy.max_concurrent,
                "priority_ordering": self.strategy.priority_ordering,
                "load_balancing": self.strategy.load_balancing,
            },
        }

    def display_status(self) -> None:
        """
        Display formatted status of all agents with visual enhancements.
        """
        from rich.panel import Panel

        from aura_cli.core.ui_bridge import UIIcons, UIStyles

        table = Table(
            title="Status dos Agentes",
            show_header=True,
            header_style=UIStyles.safe_style("SUBTITLE", "white"),
            border_style=UIStyles.safe_style("BORDER_PRIMARY", "cyan"),
            title_style=UIStyles.safe_style("TITLE", "bold white"),
            width=int(console.width * 0.95),
        )
        primary_style = UIStyles.safe_style("PRIMARY", "cyan")
        table.add_column("Agente", style=primary_style, min_width=15)
        table.add_column("Status", style=UIStyles.SECONDARY, min_width=20)
        table.add_column("Tarefas", justify="center")
        table.add_column("Completadas", justify="center")
        table.add_column("Erros", justify="center")

        for agent in self.agents.values():
            status_info = agent.get_status()

            status_text = status_info["status"]
            status_style = UIStyles.safe_style("MUTED", "dim white")
            status_icon = UIIcons.BULLET

            if status_text == "idle":
                status_style = UIStyles.safe_style("STATUS_IDLE", "dim white")
                status_icon = UIIcons.IDLE
            elif status_text == "thinking":
                status_style = UIStyles.safe_style("STATUS_THINKING", "yellow")
                status_icon = UIIcons.THINKING
            elif status_text == "working":
                status_style = UIStyles.safe_style("STATUS_WORKING", "cyan")
                status_icon = UIIcons.WORKING
                from datetime import datetime

                progress_dots = "." * (datetime.now().second % 4)
                display_status = f"[{status_style}]{status_icon} {status_text.capitalize()}{progress_dots}[/{status_style}]"
            elif status_text == "error":
                status_style = UIStyles.safe_style("STATUS_ERROR", "red")
                status_icon = UIIcons.ERROR
            elif status_text == "completed":
                status_style = UIStyles.safe_style("STATUS_SUCCESS", "green")
                status_icon = UIIcons.SUCCESS

            display_status = f"[{status_style}]{status_icon} {status_text.capitalize()}[/{status_style}]"

            table.add_row(
                agent.name,
                display_status,
                str(status_info["tasks_queued"]),
                str(status_info["tasks_completed"]),
                str(status_info["errors_count"]),
            )

        title_style = UIStyles.safe_style("TITLE", "bold white")
        border_style = UIStyles.safe_style("BORDER_ACCENT", "magenta")
        console.print(
            Panel(
                table,
                title=f"[{title_style}]Gerenciador de Agentes[/{title_style}]",
                border_style=border_style,
                expand=True,
            )
        )

    def reset_all(self) -> None:
        """
        Reset all registered agents.
        """
        for agent in self.agents.values():
            agent.reset()

        self.total_tasks_distributed = 0
        self.total_tasks_completed = 0

        logger.info("All agents have been reset")

    def __repr__(self) -> str:
        """String representation of the orchestrator."""
        return f"<AgentOrchestrator(agents={len(self.agents)}, running={self.running})>"
