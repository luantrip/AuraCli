"""
Agent Runner — Executes specialist persona agents.

Agents are defined as markdown files with YAML frontmatter specifying
configuration and a body containing the system prompt.

When an agent name maps to a registered ADK specialized agent, execution
is delegated to the ADK layer. The llm_query path is kept as fallback
for agents not yet in the ADK registry.
"""

import asyncio
import logging
from pathlib import Path
import time
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
)

from pydantic import BaseModel, Field
import yaml

from aura_cli.core.personas.models import AgentExecutionResult, AgentMetadata

logger = logging.getLogger(__name__)

AGENTS_DIR = Path(__file__).parent / "agents"

# Mapping from consciousness agent names → ADK specialized agent names
_CONSCIOUSNESS_TO_ADK: Dict[str, str] = {
    "code-reviewer-agent": "review_agent",
    "code-refactor-agent": "refactor_agent",
    "test-writer-agent": "test_agent",
    "ops-agent": "ops_agent",
    "constitution-agent": "planning_agent",  # hyphen matches frontmatter name field
}


class AgentConfig(BaseModel):
    """Configuration for an agent."""

    name: str
    description: str
    model: str = "sonnet"
    allowed_tools: List[str] = Field(default_factory=list)
    system_prompt: str = ""


class AgentRunner:
    """
    Loads and executes specialist agents.

    Agents are defined as markdown files with YAML frontmatter specifying
    configuration and a body containing the system prompt.
    """

    def __init__(self, agents_dir: Optional[Path] = None):
        """
        Initialize agent runner.

        Args:
            agents_dir: Directory containing agent markdown files
        """
        self.agents_dir = agents_dir or AGENTS_DIR
        self._agents: Dict[str, AgentConfig] = {}
        self._load_agents()

    def _load_agents(self) -> None:
        """Load agent configurations from markdown files."""
        if not self.agents_dir.exists():
            logger.warning(f"Agents directory not found: {self.agents_dir}")
            return

        for md_file in self.agents_dir.glob("**/*.md"):
            try:
                config = self._parse_agent_file(md_file)
                if config:
                    self._agents[config.name] = config
            except Exception as e:
                logger.error(f"Error loading agent {md_file}: {e}")

        logger.info(f"Loaded {len(self._agents)} agents")

    def _parse_agent_file(self, filepath: Path) -> Optional[AgentConfig]:
        """Parse agent file and extract configuration."""
        content = filepath.read_text(encoding="utf-8")

        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        try:
            frontmatter = yaml.safe_load(parts[1])
            if not frontmatter or "name" not in frontmatter:
                return None

            allowed_tools = frontmatter.get("allowed-tools", [])
            if isinstance(allowed_tools, str):
                allowed_tools = [t.strip() for t in allowed_tools.split(",")]

            return AgentConfig(
                name=frontmatter.get("name", filepath.stem),
                description=frontmatter.get("description", ""),
                model=frontmatter.get("model", "default"),
                allowed_tools=allowed_tools,
                system_prompt=parts[2].strip(),
            )
        except yaml.YAMLError as e:
            logger.error(f"YAML error in {filepath}: {e}")
            return None

    def get_agent(self, name: str) -> Optional[AgentConfig]:
        """Get agent configuration by name."""
        return self._agents.get(name)

    def list_agents(self) -> List[AgentMetadata]:
        """List all available agents."""
        return [
            AgentMetadata(
                name=config.name,
                description=config.description,
                model=config.model,
                allowed_tools=config.allowed_tools,
            )
            for config in self._agents.values()
        ]

    async def run(
        self,
        agent_name: str,
        input_data: str,
        llm_query: Callable[[str, str, str], Any],
    ) -> AgentExecutionResult:
        """
        Execute an agent with the given input.

        Args:
            agent_name: Name of the agent to run
            input_data: Input data/context for the agent
            llm_query: Async function(system_prompt, user_message, model) -> response

        Returns:
            AgentExecutionResult with output and metadata
        """
        config = self.get_agent(agent_name)
        if not config:
            return AgentExecutionResult(
                agent_name=agent_name,
                success=False,
                output="",
                error=f"Agent '{agent_name}' not found",
            )

        start_time = time.time()

        try:
            # --- ADK delegation (Fase 1.2 migration) ---
            adk_name = _CONSCIOUSNESS_TO_ADK.get(agent_name)
            if adk_name:
                try:
                    from aura_cli.adk.specialized import (
                        OpsAgent,
                        RefactorAgent,
                        ReviewAgent,
                        TestAgent,
                    )

                    _adk_map = {
                        "review_agent": ReviewAgent,
                        "refactor_agent": RefactorAgent,
                        "test_agent": TestAgent,
                        "ops_agent": OpsAgent,
                        "planning_agent": None,  # PlanningAgent not imported here
                    }
                    agent_cls = _adk_map.get(adk_name)
                    if agent_cls is not None:
                        adk_agent = agent_cls()
                        adk_response = await adk_agent.execute(input_data)
                        execution_time = time.time() - start_time
                        return AgentExecutionResult(
                            agent_name=agent_name,
                            success=adk_response.success,
                            output=adk_response.content,
                            error=adk_response.error,
                            execution_time=execution_time,
                        )
                except Exception as adk_err:
                    logger.warning(
                        f"ADK delegation failed for '{agent_name}', using llm_query: {adk_err}"
                    )
            # --- llm_query path ---
            user_message = f"Apply your instructions to the following:\n\n{input_data}"
            # Resolve model: "sonnet"/"default" → modelo configurado no sistema
            model = config.model
            if model in ("sonnet", "default", ""):
                try:
                    from aura_cli.core.llm.model_utils import DEFAULT_MODEL

                    model = DEFAULT_MODEL
                except Exception:
                    model = "cerebras/gpt-oss-120b"
            response = await llm_query(
                config.system_prompt,
                user_message,
                model,
            )

            execution_time = time.time() - start_time

            return AgentExecutionResult(
                agent_name=agent_name,
                success=True,
                output=str(response),
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Agent execution error: {e}")
            return AgentExecutionResult(
                agent_name=agent_name,
                success=False,
                output="",
                error=str(e),
                execution_time=execution_time,
            )

    def run_sync(
        self,
        agent_name: str,
        input_data: str,
        llm_query: Callable[[str, str, str], str],
    ) -> AgentExecutionResult:
        """
        Execute an agent synchronously.

        Args:
            agent_name: Name of the agent to run
            input_data: Input data/context for the agent
            llm_query: Function(system_prompt, user_message, model) -> response string

        Returns:
            AgentExecutionResult with output and metadata
        """
        config = self.get_agent(agent_name)
        if not config:
            return AgentExecutionResult(
                agent_name=agent_name,
                success=False,
                output="",
                error=f"Agent '{agent_name}' not found",
            )

        start_time = time.time()

        try:
            # --- ADK delegation via asyncio (Fase 1.2 migration) ---
            adk_name = _CONSCIOUSNESS_TO_ADK.get(agent_name)
            if adk_name:
                try:
                    from aura_cli.adk.specialized import (
                        OpsAgent,
                        RefactorAgent,
                        ReviewAgent,
                        TestAgent,
                    )

                    _adk_map = {
                        "review_agent": ReviewAgent,
                        "refactor_agent": RefactorAgent,
                        "test_agent": TestAgent,
                        "ops_agent": OpsAgent,
                    }
                    agent_cls = _adk_map.get(adk_name)
                    if agent_cls is not None:
                        adk_agent = agent_cls()  # type: ignore[abstract]
                        try:
                            loop = asyncio.get_event_loop()
                        except RuntimeError:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                        adk_response = loop.run_until_complete(
                            adk_agent.execute(input_data)
                        )
                        execution_time = time.time() - start_time
                        return AgentExecutionResult(
                            agent_name=agent_name,
                            success=adk_response.success,
                            output=adk_response.content,
                            error=adk_response.error,
                            execution_time=execution_time,
                        )
                except Exception as adk_err:
                    logger.warning(
                        f"ADK sync delegation failed for '{agent_name}', using llm_query: {adk_err}"
                    )
            # --- llm_query path ---
            user_message = f"Apply your instructions to the following:\n\n{input_data}"
            model = config.model
            if model in ("sonnet", "default", ""):
                try:
                    from aura_cli.core.llm.model_utils import DEFAULT_MODEL

                    model = DEFAULT_MODEL
                except Exception:
                    model = "cerebras/gpt-oss-120b"
            response = llm_query(
                config.system_prompt,
                user_message,
                model,
            )

            execution_time = time.time() - start_time

            return AgentExecutionResult(
                agent_name=agent_name,
                success=True,
                output=response,
                execution_time=execution_time,
            )

        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Agent execution error: {e}")
            return AgentExecutionResult(
                agent_name=agent_name,
                success=False,
                output="",
                error=str(e),
                execution_time=execution_time,
            )

    def reload(self) -> None:
        """Reload agents from disk."""
        self._agents.clear()
        self._load_agents()


_runner: Optional[AgentRunner] = None


def get_agent_runner() -> AgentRunner:
    """Get global AgentRunner instance."""
    # Try DI container first (preferred path)
    try:
        from aura_cli.core.di import Services, get_container

        container = get_container()
        if container.has(Services.AGENT_RUNNER):
            return container.resolve(Services.AGENT_RUNNER)
    except Exception:
        pass

    # Fallback to legacy singleton
    global _runner
    if _runner is None:
        _runner = AgentRunner()
    return _runner
