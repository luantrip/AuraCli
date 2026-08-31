"""ADK Agent Base Classes."""

from __future__ import annotations

from abc import ABC, abstractmethod
import asyncio
from enum import Enum
import logging
import time
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Set,
    Type,
    TypeVar,
    cast,
)

from aura_cli.adk.memory import Memory, MemoryEntry
from aura_cli.application.agents import AgentCapability, AgentConfig, AgentResponse
from aura_cli.application.agents.workflow import Workflow

logger = logging.getLogger(__name__)

T = TypeVar("T", bound="Agent")


class AgentState(Enum):
    """Agent lifecycle states."""

    IDLE = "idle"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    ERROR = "error"
    TERMINATED = "terminated"


class Agent(ABC):
    """
    Base class for all Aura agents.

    Example:
        ```python
        class MyCustomAgent(Agent):
            name = "my_agent"
            description = "A custom agent"
            capabilities = {AgentCapability.CODE_GENERATION}

            async def execute(self, task: str) -> AgentResponse:
                context = await self.recall("relevant context for the task")
                result = await self.llm_call(f"{task}\n\nContext: {context}")
                await self.remember(f"Task: {task}, Result: {result}")
                return AgentResponse(content=result, success=True)
        ```
    """

    name: str = "base_agent"
    description: str = "Base agent class"
    capabilities: ClassVar[Set[AgentCapability]] = set()
    default_tools: ClassVar[List[str]] = []

    def __init__(self, config: Optional[AgentConfig] = None):
        """
        Initialize the agent.

        Args:
            config: Optional configuration override
        """
        self.config = config or AgentConfig(
            name=self.name,
            description=self.description,
            capabilities=self.capabilities,
            tools=cast(list[str | Callable[..., Any]], list(self.default_tools)),
        )
        self.state = AgentState.IDLE
        self.memory: Optional[Memory] = None
        if self.config.memory_enabled:
            try:
                from aura_cli.adk.memory import VectorMemory

                self.memory = VectorMemory(
                    collection_name=f"agent_{self.config.name}",
                )
            except Exception as e:
                logger.warning(
                    f"Failed to initialize memory for agent {self.config.name}: {e}. "
                    "Memory will be disabled for this agent."
                )
                self.memory = None

        self._context: Dict[str, Any] = {}
        self._tools: Dict[str, Callable] = {}
        self._on_state_change: List[Callable[[AgentState], None]] = []

    def __repr__(self) -> str:
        """Return a concise string representation of the agent."""
        return (
            f"<{self.__class__.__name__}(name={self.name}, state={self.state.value})>"
        )

    async def initialize(self) -> None:
        """Initialize the agent. Override for custom initialization."""
        self._set_state(AgentState.INITIALIZING)
        await self._load_tools()
        self._set_state(AgentState.READY)
        logger.info(f"Agent {self.name} initialized")

    async def shutdown(self) -> None:
        """Shutdown the agent. Override for custom cleanup."""
        self._set_state(AgentState.TERMINATED)
        self._context.clear()
        logger.info(f"Agent {self.name} shutdown")

    def _set_state(self, state: AgentState) -> None:
        """Set agent state and notify listeners."""
        self.state = state
        for callback in self._on_state_change:
            try:
                callback(state)
            except Exception as e:
                logger.error(f"Error in state change callback: {e}")

    def on_state_change(self, callback: Callable[[AgentState], None]) -> None:
        """Register a state change callback."""
        self._on_state_change.append(callback)

    @abstractmethod
    async def execute(self, task: str, **kwargs) -> AgentResponse:
        """
        Execute a task.

        Args:
            task: The task description or prompt
            **kwargs: Additional parameters

        Returns:
            AgentResponse with the result
        """

    async def _load_tools(self) -> None:
        """Load tools specified in config."""
        from aura_cli.adk.tools import get_tool_registry

        registry = get_tool_registry()
        for tool_name in self.config.tools:
            if not isinstance(tool_name, str):
                self.register_tool(getattr(tool_name, "__name__", "tool"), tool_name)
                continue
            tool = registry.get(tool_name)
            if tool:
                self._tools[tool_name] = tool
            else:
                logger.warning(f"Tool not found: {tool_name}")

    def register_tool(self, name: str, func: Callable) -> None:
        """Register a tool for this agent."""
        self._tools[name] = func

    async def call_tool(self, name: str, **kwargs) -> Any:
        """Call a registered tool."""
        if name not in self._tools:
            raise ValueError(f"Tool not found: {name}")

        tool = self._tools[name]
        if asyncio.iscoroutinefunction(tool):
            return await tool(**kwargs)
        return tool(**kwargs)

    async def remember(
        self, content: str, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add content to the agent's memory (both conversation and long-term)."""
        if self.config.memory_enabled:
            if self.memory is None:
                try:
                    from aura_cli.adk.memory import VectorMemory

                    self.memory = VectorMemory(
                        collection_name=f"agent_{self.config.name}",
                    )
                except Exception as e:
                    logger.warning(f"Failed to initialize VectorMemory: {e}")
                    self.memory = None

            if self.memory:
                await self.memory.add(content, metadata)

    async def recall(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """Search the agent's memory (both conversation and long-term)."""
        results = []

        if self.config.memory_enabled:
            if self.memory is None:
                try:
                    from aura_cli.adk.memory import VectorMemory

                    self.memory = VectorMemory(
                        collection_name=f"agent_{self.config.name}",
                    )
                except Exception as e:
                    logger.warning(f"Failed to initialize VectorMemory: {e}")
                    self.memory = None

            if self.memory:
                local_results = await self.memory.search(query, limit)
                results.extend(local_results)

        try:
            from aura_cli.adk.memory import MemoryEntry
            from aura_cli.application.agents import get_agent_runtime

            recall_memory = get_agent_runtime().recall_memory
            remote_results = (
                await asyncio.to_thread(recall_memory, query, limit)
                if recall_memory is not None
                else []
            )

            for item in remote_results:
                entry = MemoryEntry(
                    id=item.get("id", "remote"),
                    content=item.get("content", ""),
                    metadata=item.get("metadata", {}),
                    timestamp=time.time(),  # Approximation
                )
                results.append(entry)

        except Exception as e:
            logger.warning(f"Failed to recall from MemoryService: {e}")

        unique_results = []
        seen_content = set()
        for res in results:
            if res.content not in seen_content:
                seen_content.add(res.content)
                unique_results.append(res)

        return unique_results[:limit]

    def set_context(self, key: str, value: Any) -> None:
        """Set a context value for the current task."""
        self._context[key] = value

    def get_context(self, key: str, default: Any = None) -> Any:
        """Get a context value."""
        return self._context.get(key, default)

    def clear_context(self) -> None:
        """Clear all context."""
        self._context.clear()

    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a capability."""
        return capability in self.config.capabilities

    async def think(self, prompt: str) -> str:
        """
        Internal reasoning step (chain-of-thought).

        Override this method to customize reasoning.
        """
        return f"Thinking about: {prompt}"

    async def plan(self, task: str) -> List[str]:
        """
        Create a plan for executing a task.

        Override this method for custom planning.
        """
        return [task]


class CompositeAgent(Agent):
    """
    An agent that coordinates multiple sub-agents using a workflow.

    Example:
        ```python
        composite = CompositeAgent(
            name="code_team",
            agents=[CodeAgent(), ReviewAgent(), TestAgent()]
        )
        result = await composite.execute("Build a REST API")
        ```
    """

    name = "composite_agent"
    description = "Coordinates multiple agents in a sequential workflow"

    def __init__(
        self, agents: List[Agent], config: Optional[AgentConfig] = None, **kwargs
    ):
        """Initialize the sequential workflow with a list of agents to run in order."""
        super().__init__(config)
        self.agents = agents
        self._agent_map = {agent.name: agent for agent in agents}

    async def initialize(self) -> None:
        """Initialize all sub-agents."""
        await super().initialize()
        for agent in self.agents:
            await agent.initialize()

    async def shutdown(self) -> None:
        """Shutdown all sub-agents."""
        for agent in self.agents:
            await agent.shutdown()
        await super().shutdown()

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        """Execute task by building and running a sequential workflow."""
        if not self.agents:
            return AgentResponse(
                content="", success=False, error="No agents in composite agent."
            )

        start_time = time.time()
        workflow = Workflow(name=self.name, description=self.description)

        previous_step_name = None
        for i, agent in enumerate(self.agents):
            step_name = agent.name or f"step_{i + 1}"

            if previous_step_name is None:
                current_task = task
                dependencies: list[str] = []
            else:
                current_task = f"{{{previous_step_name}}}"
                dependencies = [previous_step_name]

            workflow.add_step(
                agent=agent,
                task=current_task,
                name=step_name,
                depends_on=dependencies,
            )
            previous_step_name = step_name

        workflow_result = await workflow.run()

        if workflow_result.success:
            final_output = workflow_result.outputs.get(previous_step_name or "", "")
            success = True
            error = None
        else:
            final_output = ""
            success = False
            error = workflow_result.error or "Workflow failed without a specific error."
            logger.error(f"Workflow '{self.name}' failed: {error}")

        return AgentResponse(
            content=str(final_output),
            success=success,
            metadata={"workflow_result": workflow_result.to_dict()},
            error=error,
            execution_time=time.time() - start_time,
        )

    def get_agent(self, name: str) -> Optional[Agent]:
        """Get a sub-agent by name."""
        return self._agent_map.get(name)


_agent_registry: Dict[str, Type[Agent]] = {}


def register_agent(cls: Type[T]) -> Type[T]:
    """
    Decorator to register an agent class.

    Example:
        ```python
        @register_agent
        class MyAgent(Agent):
            name = "my_agent"
            ...
        ```
    """
    _agent_registry[cls.name] = cls
    return cls


def get_agent_class(name: str) -> Optional[Type[Agent]]:
    """Get a registered agent class by name."""
    return _agent_registry.get(name)


def list_agents() -> List[str]:
    """List all registered agent names."""
    return list(_agent_registry.keys())


def create_agent(name: str, config: Optional[AgentConfig] = None) -> Optional[Agent]:
    """Create an agent instance by name."""
    cls = get_agent_class(name)
    if cls:
        return cls(config=config)
    return None
