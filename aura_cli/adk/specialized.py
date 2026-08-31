"""ADK Specialized Agents powered by Consciousness personas."""

from __future__ import annotations

import asyncio
import contextlib
import logging
from typing import ClassVar

from aura_cli.adk.agent import (
    Agent,
    AgentCapability,
    AgentResponse,
    AgentState,
    register_agent,
)
from aura_cli.application.agents import get_agent_runtime

logger = logging.getLogger(__name__)


class SpecializedAgent(Agent):
    """Base class for specialized agents using personas."""

    persona_name: str = ""

    async def initialize(self) -> None:
        """Initialize agent and load persona."""
        await super().initialize()

        if self.persona_name:
            persona_config = None
            with contextlib.suppress(Exception):
                persona_config = get_agent_runtime().load_persona(self.persona_name)

            if persona_config:
                self.config.system_prompt = getattr(
                    persona_config, "system_prompt", self.config.system_prompt
                )
                self.config.description = getattr(
                    persona_config, "description", self.config.description
                )
                logger.info(
                    f"Loaded persona '{self.persona_name}' for agent {self.name}"
                )
            else:
                logger.debug(
                    f"Persona '{self.persona_name}' not found for agent {self.name}"
                )

    async def _execute_llm(self, user_message: str, **kwargs) -> str:
        """Execute LLM query with system prompt and tools."""
        messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": user_message},
        ]

        runtime = get_agent_runtime()
        tools = runtime.build_tool_schemas(
            [str(tool) for tool in self.config.tools if isinstance(tool, str)]
        )
        response = await asyncio.to_thread(
            runtime.query_llm,
            model=self.config.model,
            messages=messages,
            tools=tools or None,
        )

        return response


@register_agent
class CodeAgent(SpecializedAgent):
    """Agent specialized in code generation and analysis."""

    name = "code_agent"
    persona_name = "code-refactor-agent"
    description = "Generates and analyzes code"
    capabilities: ClassVar[set] = {
        AgentCapability.CODE_GENERATION,
        AgentCapability.ANALYSIS,
        AgentCapability.DOCUMENTATION,
    }
    default_tools: ClassVar[list] = ["read_file", "write_file", "find_in_files"]

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        """Execute code generation/analysis task."""
        self._set_state(AgentState.RUNNING)

        try:
            language = kwargs.get("language", "python")
            code = kwargs.get("code", "")

            # Construct a rich prompt
            prompt = f"Task: {task}\n\nLanguage: {language}"
            if code:
                prompt += f"\n\nCode Context:\n```\n{code}\n```"

            result = await self._execute_llm(prompt)

            self._set_state(AgentState.COMPLETED)
            return AgentResponse(
                content=result,
                success=True,
                metadata={"language": language, "task_type": "code_generation"},
            )

        except Exception as e:
            self._set_state(AgentState.ERROR)
            logger.error(f"CodeAgent error: {e}")
            return AgentResponse(
                content="",
                success=False,
                error=str(e),
            )


@register_agent
class ReviewAgent(SpecializedAgent):
    """Agent specialized in code review."""

    name = "review_agent"
    persona_name = "code-reviewer-agent"
    description = "Reviews code for quality and issues"
    capabilities: ClassVar[set] = {
        AgentCapability.CODE_REVIEW,
        AgentCapability.ANALYSIS,
    }
    default_tools: ClassVar[list] = ["read_file", "find_in_files"]

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        """Execute code review task."""
        self._set_state(AgentState.RUNNING)

        try:
            code = kwargs.get("code", "")
            review_type = kwargs.get("review_type", "general")

            prompt = f"Task: {task}\nReview Type: {review_type}"
            if code:
                prompt += f"\n\nCode to Review:\n```\n{code}\n```"

            result = await self._execute_llm(prompt)

            self._set_state(AgentState.COMPLETED)
            return AgentResponse(
                content=result,
                success=True,
                metadata={"review_type": review_type},
            )

        except Exception as e:
            self._set_state(AgentState.ERROR)
            return AgentResponse(
                content="",
                success=False,
                error=str(e),
            )


@register_agent
class RefactorAgent(SpecializedAgent):
    """Agent specialized in code refactoring."""

    name = "refactor_agent"
    persona_name = "code-refactor-agent"
    description = "Refactors and improves code structure"
    capabilities: ClassVar[set] = {
        AgentCapability.CODE_REFACTORING,
        AgentCapability.ANALYSIS,
    }
    default_tools: ClassVar[list] = ["read_file", "write_file", "find_in_files"]

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        """Execute refactoring task."""
        self._set_state(AgentState.RUNNING)

        try:
            code = kwargs.get("code", "")

            prompt = f"Refactoring Task: {task}"
            if code:
                prompt += f"\n\nCode to Refactor:\n```\n{code}\n```"

            result = await self._execute_llm(prompt)

            self._set_state(AgentState.COMPLETED)
            return AgentResponse(
                content=result,
                success=True,
                metadata={"refactoring_type": "general"},
            )

        except Exception as e:
            self._set_state(AgentState.ERROR)
            return AgentResponse(
                content="",
                success=False,
                error=str(e),
            )


@register_agent
class TestAgent(SpecializedAgent):
    """Agent specialized in test generation."""

    name = "test_agent"
    persona_name = "test-writer-agent"
    description = "Generates and analyzes tests"
    capabilities: ClassVar[set] = {
        AgentCapability.TEST_GENERATION,
        AgentCapability.ANALYSIS,
    }
    default_tools: ClassVar[list] = ["read_file", "write_file", "run_tests_advanced"]

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        """Execute test generation task."""
        self._set_state(AgentState.RUNNING)

        try:
            code = kwargs.get("code", "")
            test_type = kwargs.get("test_type", "unit")

            prompt = f"Task: {task}\nTest Type: {test_type}"
            if code:
                prompt += f"\n\nCode to Test:\n```\n{code}\n```"

            result = await self._execute_llm(prompt)

            self._set_state(AgentState.COMPLETED)
            return AgentResponse(
                content=result,
                success=True,
                metadata={"test_type": test_type},
            )

        except Exception as e:
            self._set_state(AgentState.ERROR)
            return AgentResponse(
                content="",
                success=False,
                error=str(e),
            )


@register_agent
class PlanningAgent(SpecializedAgent):
    """Agent specialized in task planning."""

    name = "planning_agent"
    persona_name = "constitution_agent"  # Fallback/Closest match
    description = "Plans and decomposes complex tasks"
    capabilities: ClassVar[set] = {
        AgentCapability.PLANNING,
        AgentCapability.ANALYSIS,
    }

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        """Execute planning task."""
        self._set_state(AgentState.RUNNING)

        try:
            prompt = f"Create a detailed execution plan for the following task:\n{task}"

            result = await self._execute_llm(prompt)

            self._set_state(AgentState.COMPLETED)
            return AgentResponse(
                content=result,
                success=True,
                metadata={"task": task},
            )

        except Exception as e:
            self._set_state(AgentState.ERROR)
            return AgentResponse(
                content="",
                success=False,
                error=str(e),
            )


@register_agent
class OpsAgent(SpecializedAgent):
    """Agent specialized in DevOps operations."""

    name = "ops_agent"
    persona_name = "ops-agent"
    description = "DevOps specialist for infrastructure and operations"
    capabilities: ClassVar[set] = {
        AgentCapability.SHELL_EXECUTION,
        AgentCapability.FILE_OPERATIONS,
        AgentCapability.ANALYSIS,
    }

    async def execute(self, task: str, **kwargs) -> AgentResponse:
        """Execute DevOps task."""
        self._set_state(AgentState.RUNNING)

        try:
            prompt = f"Execute the following DevOps task:\n{task}"

            result = await self._execute_llm(prompt)

            self._set_state(AgentState.COMPLETED)
            return AgentResponse(
                content=result,
                success=True,
                metadata={
                    "agent": "ops",
                    "task": task,
                },
            )

        except Exception as e:
            self._set_state(AgentState.ERROR)
            return AgentResponse(
                content="",
                success=False,
                error=str(e),
            )
