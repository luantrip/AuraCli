"""
Pydantic models for Skills and Agents.
"""

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field


class SkillMetadata(BaseModel):
    """Metadata for a skill file."""

    name: str = Field(..., description="Unique skill name")
    description: str = Field(
        ..., description="Description used for semantic search matching"
    )
    version: str = Field(default="1.0.0", description="Semantic version")
    author: str = Field(default="Aura Core Team", description="Skill author")
    filepath: Optional[Path] = Field(default=None, description="Path to skill file")

    model_config = {"arbitrary_types_allowed": True}


class AgentMetadata(BaseModel):
    """Metadata for an agent file."""

    name: str = Field(..., description="Unique agent name")
    description: str = Field(..., description="Agent purpose description")
    model: str = Field(default="sonnet", description="Preferred LLM model")
    allowed_tools: List[str] = Field(
        default_factory=list, description="Tools this agent can use"
    )
    filepath: Optional[Path] = Field(default=None, description="Path to agent file")

    model_config = {"arbitrary_types_allowed": True}


class SkillMatch(BaseModel):
    """Result of skill matching."""

    skill: SkillMetadata
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    content: str = Field(..., description="Full skill content")


class AgentExecutionResult(BaseModel):
    """Result of agent execution."""

    agent_name: str
    success: bool
    output: str
    error: Optional[str] = None
    tokens_used: Optional[int] = None
    execution_time: Optional[float] = None
