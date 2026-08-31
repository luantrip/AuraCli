"""Adapt asynchronous ADK agents to the synchronous ``AgentBase`` boundary.

The wrapper translates task/response schemas, tools and memory while containing
event-loop bridging required by ``AgentOrchestrator`` and ``WorkflowExecutor``.
It remains necessary until those Core consumers adopt the asynchronous agent
protocol directly.

Usage:
    >>> from aura_cli.core.agents.adk_wrapper import ADKAgentWrapper
    >>> from aura_cli.adk import CodeAgent
    >>>
    >>> adk_agent = CodeAgent()
    >>> wrapper = ADKAgentWrapper(
    ...     adk_agent=adk_agent,
    ...     agent_id="code_agent",
    ...     model="gpt-4o"
    ... )
    >>>
    >>> # Now can be used with orchestrator
    >>> orchestrator.register_agent(wrapper)
"""

from __future__ import annotations

import asyncio
import threading
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from aura_cli.core.agents.agent_base import AgentBase, AgentContext, AgentTask
from aura_cli.core.logger import get_logger

if TYPE_CHECKING:
    from aura_cli.adk.agent import Agent, AgentResponse

logger = get_logger(__name__)


class ADKAgentWrapper(AgentBase):
    """
    Wrapper that adapts ADK Agent to AgentBase interface.

    Allows ADK agents to be used with the synchronous Core orchestrator and workflows
    by converting between async ADK interface and sync AgentBase interface.

    Key Adaptations:
        - Core AgentTask ↔ task string (ADK)
        - sync execute_next_task() → async execute()
        - AgentResponse (ADK) → Core result
        - ADK tools → Core tool schemas
    """

    def __init__(
        self,
        adk_agent: Agent,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        model: Optional[str] = None,
        context: Optional[AgentContext] = None,
        memory_synchronizer: Any = None,
    ):
        """
        Initialize ADK wrapper.

        Args:
            adk_agent: ADK Agent instance to wrap
            agent_id: Agent ID (None = use from adk_agent.config.name)
            name: Agent name (None = use from adk_agent)
            description: Agent description (None = use from adk_agent)
            model: LLM model (None = use from adk_agent.config.model)
            context: Shared context (None = create new)
        """
        agent_id = agent_id or adk_agent.config.name or adk_agent.name
        name = name or adk_agent.name or adk_agent.config.name
        description = (
            description or adk_agent.description or adk_agent.config.description or ""
        )
        model = model or adk_agent.config.model

        super().__init__(
            agent_id=agent_id,
            name=name,
            description=description,
            model=model,
            context=context,
        )

        self.adk_agent = adk_agent
        self._memory_synchronizer = memory_synchronizer
        self._event_loop: Optional[asyncio.AbstractEventLoop] = None
        self._loop_lock = threading.Lock()
        self._loop_thread_id: Optional[int] = None
        self._ensure_adk_initialized()

        logger.info(
            f"ADKAgentWrapper created for {self.name} "
            f"(wrapping {adk_agent.__class__.__name__})"
        )

    def _ensure_adk_initialized(self) -> None:
        """Ensure ADK agent is initialized."""
        try:
            if hasattr(self.adk_agent, "state"):
                from aura_cli.adk.agent import AgentState

                current_state = getattr(self.adk_agent, "state", None)
                if current_state == AgentState.IDLE:
                    try:
                        loop = self._get_event_loop()
                        if loop.is_running():
                            asyncio.run_coroutine_threadsafe(
                                self.adk_agent.initialize(), loop
                            )
                        else:
                            loop.run_until_complete(self.adk_agent.initialize())
                    except Exception as init_error:
                        logger.debug(
                            f"Could not initialize ADK agent now: {init_error}"
                        )
        except Exception as e:
            logger.debug(f"Could not check ADK agent initialization: {e}")

    def _get_event_loop(self) -> asyncio.AbstractEventLoop:
        """
        Get or create event loop for async execution.

        Thread-safe event loop management. Creates a new loop if needed
        or reuses existing one in the current thread.
        """
        with self._loop_lock:
            current_thread_id = threading.current_thread().ident

            if (
                self._loop_thread_id != current_thread_id
                or self._event_loop is None
                or self._event_loop.is_closed()
            ):
                try:
                    # Python 3.10+: get_event_loop() emits DeprecationWarning when
                    # there is no running loop — use get_running_loop() first.
                    loop = asyncio.get_running_loop()
                    if self._loop_thread_id != current_thread_id:
                        raise RuntimeError("Different thread")
                except RuntimeError:
                    # No running loop or different thread — create a new one.
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                except AttributeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                self._event_loop = loop
                self._loop_thread_id = current_thread_id

            return self._event_loop

    def _execute_task(self, task: AgentTask) -> Any:
        """
        Execute task by adapting AgentTask to ADK format.

        Converts:
            - AgentTask → task string + parameters
            - Calls adk_agent.execute() async
            - AgentResponse → result

        Args:
            task: Core AgentTask

        Returns:
            Execution result (converted from AgentResponse)

        Raises:
            RuntimeError: If ADK agent execution fails
        """
        task_string = self._task_to_string(task)
        kwargs = task.parameters.copy()

        try:
            loop = self._get_event_loop()

            if loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self.adk_agent.execute(task_string, **kwargs), loop
                )
                response = future.result(timeout=300.0)
            else:
                try:
                    response = loop.run_until_complete(
                        self.adk_agent.execute(task_string, **kwargs)
                    )
                except RuntimeError as e:
                    if "cannot be called from a running event loop" in str(e):
                        response = asyncio.run(
                            self.adk_agent.execute(task_string, **kwargs)
                        )
                    else:
                        raise

            self._track_execution_metrics(response)
            return self._response_to_result(response)

        except asyncio.TimeoutError:
            error_msg = "ADK agent execution timed out"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from None
        except Exception as e:
            error_msg = f"ADK agent execution failed: {e}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from e

    def _task_to_string(self, task: AgentTask) -> str:
        """
        Convert AgentTask to task string for ADK.

        Args:
            task: Core AgentTask

        Returns:
            Task string for ADK agent
        """
        task_str = task.description
        parts = [task_str]

        task_type = task.parameters.get("type")
        if task_type:
            parts.insert(0, f"Type: {task_type}")

        important_params = {}
        for key in ["path", "file_path", "pattern", "command", "container", "language"]:
            if key in task.parameters:
                important_params[key] = task.parameters[key]

        if important_params:
            params_list = [f"{k}: {v}" for k, v in important_params.items()]
            parts.append(f"Parameters: {', '.join(params_list)}")

        return "\n".join(parts) if len(parts) > 1 else task_str

    def _response_to_result(self, response: AgentResponse) -> Any:
        """
        Convert an ADK AgentResponse to the Core AgentBase result contract.

        Args:
            response: AgentResponse from ADK agent

        Returns:
            Result compatible with Core AgentBase

        Raises:
            RuntimeError: If response indicates failure
        """
        if response.success:
            result = response.content

            if response.metadata:
                self.context.shared_memory["last_execution_metadata"] = (
                    response.metadata
                )

            self._sync_memory_after_execution(result, response.metadata)
            return result
        else:
            error_msg = response.error or "Task execution failed"
            logger.error(f"ADK agent returned error: {error_msg}")
            raise RuntimeError(error_msg)

    def _sync_memory_after_execution(
        self, result: Any, metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Synchronize memory bidirectionally after task execution.

        This ensures that memories from ADK ConversationMemory and keyed AgentMemory
        are synchronized automatically.

        Args:
            result: Execution result
            metadata: Optional metadata from execution
        """
        try:
            bridge = self._memory_synchronizer
            if bridge is None:
                return

            if not bridge._sync_enabled:
                return

            adk_memory = getattr(self.adk_agent, "memory", None)
            if not adk_memory:
                return

            agent_memory = self.context.shared_memory.get("agent_memory_service")
            if not agent_memory:
                return
            if bridge._agent_memory is None:
                bridge.set_agent_memory(agent_memory)

            try:
                loop = self._get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        bridge.bidirectional_sync(
                            agent_id=self.agent_id,
                            conversation_memory=adk_memory,
                            limit=50,
                        ),
                        loop,
                    )
                else:
                    loop.run_until_complete(
                        bridge.bidirectional_sync(
                            agent_id=self.agent_id,
                            conversation_memory=adk_memory,
                            limit=50,
                        )
                    )
            except Exception as sync_error:
                logger.debug(
                    f"Memory sync scheduled but not executed immediately: {sync_error}"
                )

        except ImportError:
            logger.debug("MemoryBridge not available, skipping memory sync")
        except Exception as e:
            logger.debug(f"Error syncing memory after execution: {e}")

    def _track_execution_metrics(self, response: AgentResponse) -> None:
        """
        Track execution metrics in the Metrics Bridge.

        Args:
            response: AgentResponse from ADK agent
        """
        try:
            from aura_cli.application.observability import get_telemetry_coordinator

            bridge = get_telemetry_coordinator()
            execution_time = getattr(response, "execution_time", 0.0)
            tokens = response.metadata.get("tokens", 0) if response.metadata else 0

            bridge.track_adk_execution(
                agent_id=self.agent_id,
                execution_time=execution_time,
                tokens=tokens,
                success=response.success,
                error=response.error,
            )

        except ImportError:
            logger.debug("MetricsBridge not available, skipping metrics tracking")
        except Exception as e:
            logger.debug(f"Error tracking execution metrics: {e}")

    def _get_available_tools(self) -> List[Dict[str, Any]]:
        """
        Get available tools in the shared OpenAI function-schema format.

        Returns:
            List of tool schemas in OpenAI function calling format
        """
        try:
            from aura_cli.adk.tools import get_tool_registry

            registry = get_tool_registry()
            tools = []

            for tool_name in registry.list_tools():
                schema = registry.get_schema(tool_name)

                if schema:
                    tools.append(schema.to_openai_schema())
                else:
                    tool = registry.get(tool_name)
                    if tool:
                        tools.append(
                            {
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "description": f"Tool: {tool_name}",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {},
                                        "required": [],
                                    },
                                },
                            }
                        )

            try:
                from aura_cli.core.service_registry import get_tools_dict

                core_tools = get_tools_dict()

                for tool_name, _tool_func in core_tools.items():
                    if not any(
                        t.get("function", {}).get("name") == tool_name for t in tools
                    ):
                        tools.append(
                            {
                                "type": "function",
                                "function": {
                                    "name": tool_name,
                                    "description": f"Core tool: {tool_name}",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {},
                                        "required": [],
                                    },
                                },
                            }
                        )
            except Exception as e:
                logger.debug(f"Could not merge Core tools: {e}")

            return tools

        except Exception as e:
            logger.warning(f"Could not get ADK tools: {e}")
            return []

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

        if hasattr(self, "consciousness_persona") and self.consciousness_persona:
            persona_section = (
                f"\n\n## 🎭 Persona: {self.consciousness_persona.get('name', 'Specialist')}\n\n"
                f"{self.consciousness_persona.get('system_prompt', '')}"
            )
            parts.append(persona_section)

        if hasattr(self, "consciousness_skills") and self.consciousness_skills:
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
        return bool(
            (hasattr(self, "consciousness_persona") and self.consciousness_persona)
            or (hasattr(self, "consciousness_skills") and self.consciousness_skills)
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"<ADKAgentWrapper(id={self.agent_id}, name={self.name}, "
            f"wrapping={self.adk_agent.__class__.__name__})>"
        )
