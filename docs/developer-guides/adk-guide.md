# Aura Agent Development Kit (ADK) Guide

The Aura ADK provides a comprehensive framework for building, deploying, and managing AI agents within the Aura CLI ecosystem.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Core Concepts](#core-concepts)
3. [Creating Agents](#creating-agents)
4. [Working with Tools](#working-with-tools)
5. [Building Workflows](#building-workflows)
6. [Memory Management](#memory-management)
7. [Metrics & Monitoring](#metrics--monitoring)
8. [Best Practices](#best-practices)
9. [API Reference](#api-reference)

---

## Quick Start

### Installation

The ADK is included with Aura CLI. Install from source:

```bash
git clone https://github.com/luantrip/AuraCli.git
cd AuraCli
pip install -e .
```

### Your First Agent

```python
from aura_cli.adk import Agent, AgentResponse

# 1. Create a simple agent
class GreeterAgent(Agent):
    name = "greeter"
    description = "A friendly greeting agent"
    
    async def execute(self, task: str, **kwargs) -> AgentResponse:
        name = kwargs.get("name", "World")
        return AgentResponse(
            content=f"Hello, {name}! You asked: {task}",
            success=True
        )

# 2. Use the agent
agent = GreeterAgent()
await agent.initialize()
result = await agent.execute("Say hello", name="Developer")
print(result.content)  # "Hello, Developer! You asked: Say hello"
await agent.shutdown()
```

### Using Built-in Agents

```python
from aura_cli.adk import CodeAgent, ReviewAgent, TestAgent

# Use specialized agents directly
code_agent = CodeAgent()
await code_agent.initialize()

result = await code_agent.execute("Create a Python function to calculate factorial")
print(result.content)  # Generated code

await code_agent.shutdown()
```

### Quick Example: Code Review Workflow

```python
from aura_cli.adk import CodeAgent, ReviewAgent, Workflow

# Create workflow
workflow = Workflow("code_review")

# Step 1: Generate code
workflow.add_step(
    CodeAgent(),
    "Create a REST API endpoint for user authentication",
    name="generate"
)

# Step 2: Review code
workflow.add_step(
    ReviewAgent(),
    "Review this code: {generate.output}",
    name="review",
    depends_on=["generate"]
)

# Run workflow
result = await workflow.run()
print(f"Success: {result.success}")
print(f"Review: {result.steps['review'].output}")
```

---

## Core Concepts

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        ADK Layer                            │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │ Agents  │  │  Tools  │  │Workflows│  │ Memory  │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       │            │            │            │              │
│  ┌────┴────────────┴────────────┴────────────┴────┐        │
│  │              Orchestrator                       │        │
│  └────────────────────┬───────────────────────────┘        │
│                       │                                     │
│  ┌────────────────────┴───────────────────────────┐        │
│  │               Metrics Collector                 │        │
│  └─────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Purpose |
|-----------|---------|
| **Agent** | Base class for AI agents that perform tasks |
| **Tool** | Functions that agents can call to interact with the environment |
| **Workflow** | Orchestrates multi-step agent operations |
| **Memory** | Stores conversation history and context |
| **Metrics** | Tracks performance and usage statistics |

---

## Creating Agents

### Basic Agent

```python
from aura_cli.adk import Agent, AgentConfig, AgentResponse, AgentCapability

class MyAgent(Agent):
    name = "my_agent"
    description = "Does something useful"
    capabilities = {AgentCapability.CODE_GENERATION}
    
    async def execute(self, task: str, **kwargs) -> AgentResponse:
        # Your agent logic here
        result = f"Processed: {task}"
        
        return AgentResponse(
            content=result,
            success=True,
            metadata={"processed_at": time.time()}
        )
```

### Agent with Configuration

```python
config = AgentConfig(
    name="configured_agent",
    description="Agent with custom config",
    model="gpt-4",
    temperature=0.5,
    max_tokens=2048,
    capabilities={AgentCapability.ANALYSIS},
    tools=["read_file", "search_code"],
)

agent = MyAgent(config=config)
```

### Agent Lifecycle

```python
# Initialize
await agent.initialize()

# Execute tasks
result = await agent.execute("Do something")

# Check state
print(agent.state)  # AgentState.READY

# Shutdown
await agent.shutdown()
```

### Composite Agents

Combine multiple agents:

```python
from aura_cli.adk import CompositeAgent, CodeAgent, ReviewAgent, TestAgent

team = CompositeAgent(
    agents=[CodeAgent(), ReviewAgent(), TestAgent()],
    config=AgentConfig(name="dev_team")
)

result = await team.execute("Build a REST API endpoint")
```

---

## Working with Tools

### Creating Tools (Decorator)

```python
from aura_cli.adk import tool, ToolCategory

@tool(name="read_file", description="Read file contents", category=ToolCategory.FILE_SYSTEM)
async def read_file(path: str) -> str:
    """Read and return file contents."""
    with open(path) as f:
        return f.read()

@tool(name="write_file", description="Write to file")
async def write_file(path: str, content: str) -> bool:
    """Write content to file."""
    with open(path, 'w') as f:
        f.write(content)
    return True
```

### Creating Tools (Class)

```python
from aura_cli.adk import Tool, ToolResult, ToolCategory

class SearchTool(Tool):
    name = "search_code"
    description = "Search for code patterns"
    category = ToolCategory.CODE
    
    async def execute(self, query: str, path: str = ".") -> ToolResult:
        # Search logic here
        results = ["file1.py:10", "file2.py:25"]
        return ToolResult.ok(results)
```

### Using the Tool Registry

```python
from aura_cli.adk import get_tool_registry

registry = get_tool_registry()

# List all tools
print(registry.list_tools())

# Execute a tool
result = await registry.execute("read_file", path="config.py")

# Get tool schema (for LLM)
schemas = registry.get_openai_schemas()
```

---

## Building Workflows

### Simple Workflow

```python
from aura_cli.adk import Workflow, CodeAgent, ReviewAgent, TestAgent

# Create workflow
workflow = Workflow("code_development")

# Add steps
workflow.add_step(
    CodeAgent(),
    "Write a function to calculate fibonacci numbers",
    name="generate_code"
)

workflow.add_step(
    ReviewAgent(),
    "Review the code: {generate_code.output}",
    name="review",
    depends_on=["generate_code"]
)

workflow.add_step(
    TestAgent(),
    "Write tests for: {generate_code.output}",
    name="test",
    depends_on=["generate_code"]
)

# Run workflow
result = await workflow.run()

print(f"Success: {result.success}")
print(f"Duration: {result.duration:.2f}s")
```

### Workflow Builder (Fluent API)

```python
from aura_cli.adk import WorkflowBuilder

workflow = (
    WorkflowBuilder("api_development")
    .add(CodeAgent(), "Design the API endpoints")
    .add(CodeAgent(), "Implement the endpoints", depends_on=["step_1"])
    .parallel([
        (TestAgent(), "Write unit tests"),
        (ReviewAgent(), "Review implementation"),
    ], depends_on=["step_2"])
    .build()
)

result = await workflow.run()
```

### Workflow with Conditions

```python
workflow.add_step(
    RefactorAgent(),
    "Refactor if needed",
    name="refactor",
    depends_on=["review"],
    condition=lambda outputs: "issues found" in outputs.get("review", "").lower()
)
```

---

## Memory Management

### Conversation Memory

```python
from aura_cli.adk import ConversationMemory

memory = ConversationMemory(max_turns=50, max_tokens=8000)

# Add messages
memory.add_user_message("Hello!")
memory.add_assistant_message("Hi! How can I help?")

# Get context
context = memory.get_context()
```

### Vector Memory (Semantic Search)

```python
from aura_cli.adk import VectorMemory

memory = VectorMemory()

# Add entries
await memory.add("Python is a programming language", {"topic": "programming"})
await memory.add("TypeScript adds types to JavaScript", {"topic": "programming"})

# Semantic search
results = await memory.search("What language has static types?", limit=5)
```

### Persistent Memory

```python
from aura_cli.adk import PersistentMemory
from pathlib import Path

memory = PersistentMemory(Path("~/.aura/memory.json"))

# Use like any other memory
await memory.add("Important information")

# Auto-saves on add/delete
# Or manually save
memory.save()
```

---

## Metrics & Monitoring

### Recording Metrics

```python
from aura_cli.adk import get_metrics_collector, track_performance

collector = get_metrics_collector()

# Record agent execution
collector.record_agent_execution(
    agent_name="code_agent",
    success=True,
    time_seconds=2.5,
    tokens=1500
)

# Record custom metric
collector.record_metric("api_calls", 1, endpoint="/generate")
```

### Performance Tracking

```python
from aura_cli.adk import track_performance

with track_performance("code_generation") as tracker:
    # Do work
    result = await agent.execute(task)
    tracker.add_metric("lines_generated", 100)

print(f"Duration: {tracker.duration:.2f}s")
```

### Getting Statistics

```python
summary = collector.get_summary()
print(f"Total executions: {summary['total_executions']}")
print(f"Success rate: {summary['overall_success_rate']:.1f}%")

# Agent-specific metrics
agent_metrics = collector.get_agent_metrics("code_agent")
print(f"Average time: {agent_metrics.average_time:.2f}s")
print(f"P95 time: {agent_metrics.p95_time:.2f}s")
```

---

## Best Practices

### 1. Use Type Hints

```python
async def execute(self, task: str, **kwargs) -> AgentResponse:
    language: str = kwargs.get("language", "python")
    ...
```

### 2. Handle Errors Gracefully

```python
async def execute(self, task: str, **kwargs) -> AgentResponse:
    try:
        result = await self._do_work(task)
        return AgentResponse(content=result, success=True)
    except SpecificError as e:
        logger.error(f"Known error: {e}")
        return AgentResponse(content="", success=False, error=str(e))
    except Exception as e:
        logger.exception("Unexpected error")
        return AgentResponse(content="", success=False, error="Internal error")
```

### 3. Use Context for State

```python
# Store state
self.set_context("last_result", result)
self.set_context("iteration", self.get_context("iteration", 0) + 1)

# Retrieve state
previous = self.get_context("last_result")
```

### 4. Log Important Events

```python
import logging
logger = logging.getLogger(__name__)

async def execute(self, task: str, **kwargs) -> AgentResponse:
    logger.info(f"Starting task: {task[:50]}...")
    # ...
    logger.debug(f"Intermediate result: {intermediate}")
    # ...
    logger.info(f"Completed task in {duration:.2f}s")
```

### 5. Test Your Agents

```python
import pytest
from aura_cli.adk import CodeAgent

@pytest.mark.asyncio
async def test_code_agent():
    agent = CodeAgent()
    await agent.initialize()
    
    result = await agent.execute("Create a hello world function")
    
    assert result.success
    assert "def" in result.content or "function" in result.content
    
    await agent.shutdown()
```

---

## API Reference

### Agent Classes

| Class | Description |
|-------|-------------|
| `Agent` | Base class for all agents |
| `CompositeAgent` | Coordinates multiple agents |
| `CodeAgent` | Code generation and analysis |
| `ReviewAgent` | Code review |
| `RefactorAgent` | Code refactoring |
| `TestAgent` | Test generation |
| `PlanningAgent` | Task planning and decomposition |
| `OpsAgent` | DevOps operations (git, docker, CI/CD) |

### Tool Classes

| Class/Function | Description |
|----------------|-------------|
| `Tool` | Base class for tools |
| `@tool` | Decorator to create tools |
| `ToolRegistry` | Central tool registry |
| `ToolResult` | Tool execution result |

### Workflow Classes

| Class | Description |
|-------|-------------|
| `Workflow` | Multi-step workflow orchestrator |
| `WorkflowStep` | Single step in a workflow |
| `WorkflowBuilder` | Fluent API for building workflows |
| `WorkflowResult` | Workflow execution result |

### Memory Classes

| Class | Description |
|-------|-------------|
| `Memory` | Abstract base class |
| `MemoryStore` | Simple in-memory store |
| `ConversationMemory` | Conversation history with sliding window |
| `VectorMemory` | Semantic search with embeddings |
| `PersistentMemory` | File-based persistence |

### Metrics Classes

| Class/Function | Description |
|----------------|-------------|
| `MetricsCollector` | Central metrics collection |
| `AgentMetrics` | Per-agent statistics |
| `PerformanceTracker` | Operation timing |
| `get_metrics_collector()` | Get global collector |

---

## Examples

### Example 1: Simple Code Generator

```python
from aura_cli.adk import CodeAgent

agent = CodeAgent()
await agent.initialize()

result = await agent.execute(
    "Create a Python class for managing a todo list with add, remove, and list methods"
)

print(result.content)
await agent.shutdown()
```

### Example 2: Multi-Agent Workflow

```python
from aura_cli.adk import CodeAgent, ReviewAgent, TestAgent, Workflow

workflow = Workflow("full_development")

# Generate code
workflow.add_step(CodeAgent(), "Create a calculator class", name="code")

# Review
workflow.add_step(
    ReviewAgent(),
    "Review: {code.output}",
    name="review",
    depends_on=["code"]
)

# Generate tests
workflow.add_step(
    TestAgent(),
    "Write tests for: {code.output}",
    name="tests",
    depends_on=["code"]
)

result = await workflow.run()
```

### Example 3: Custom Tool Integration

```python
from aura_cli.adk import tool, ToolCategory, Agent

@tool(name="get_weather", category=ToolCategory.WEB)
async def get_weather(city: str) -> dict:
    """Get weather for a city."""
    # Implementation
    return {"city": city, "temp": "72°F"}

class WeatherAgent(Agent):
    name = "weather"
    
    async def execute(self, task: str, **kwargs) -> AgentResponse:
        # Tool is automatically available
        weather = await self.call_tool("get_weather", city="San Francisco")
        return AgentResponse(content=str(weather), success=True)
```

### Example 4: Memory Management

```python
from aura_cli.adk import Agent, ConversationMemory

class MemoryAgent(Agent):
    def __init__(self):
        super().__init__()
        self.memory = ConversationMemory(max_turns=10)
    
    async def execute(self, task: str, **kwargs) -> AgentResponse:
        # Add to memory
        self.memory.add_user_message(task)
        
        # Get context
        context = self.memory.get_context()
        
        # Process with context
        result = await self._process_with_context(task, context)
        
        # Save response
        self.memory.add_assistant_message(result)
        
        return AgentResponse(content=result, success=True)
```

## Common Patterns

### Pattern 1: Error Handling

```python
async def execute(self, task: str, **kwargs) -> AgentResponse:
    try:
        result = await self._do_work(task)
        return AgentResponse(content=result, success=True)
    except ValueError as e:
        return AgentResponse(
            content="",
            success=False,
            error=f"Invalid input: {e}"
        )
    except Exception as e:
        logger.exception("Unexpected error")
        return AgentResponse(
            content="",
            success=False,
            error="Internal error occurred"
        )
```

### Pattern 2: Tool Chaining

```python
async def execute(self, task: str, **kwargs) -> AgentResponse:
    # Step 1: Read file
    file_content = await self.call_tool("read_file", path="data.json")
    
    # Step 2: Process
    processed = await self.call_tool("process_data", data=file_content)
    
    # Step 3: Write result
    await self.call_tool("write_file", path="output.json", content=processed)
    
    return AgentResponse(content="Processing complete", success=True)
```

### Pattern 3: Conditional Workflows

```python
workflow = Workflow("smart_development")

workflow.add_step(CodeAgent(), "Generate code", name="code")
workflow.add_step(
    ReviewAgent(),
    "Review: {code.output}",
    name="review",
    depends_on=["code"],
    condition=lambda outputs: "complex" in outputs.get("code", "").lower()
)
```

## Troubleshooting

### Agent Not Initializing

```python
# Make sure to call initialize()
agent = MyAgent()
await agent.initialize()  # Required!
result = await agent.execute("task")
```

### Tool Not Found

```python
# Register tool before using
from aura_cli.adk import get_tool_registry

registry = get_tool_registry()
registry.register(my_tool)

# Or use @tool decorator
@tool(name="my_tool")
async def my_tool():
    pass
```

### Memory Issues

```python
# Limit memory size
memory = ConversationMemory(max_turns=50, max_tokens=8000)

# Or use vector memory for large datasets
from aura_cli.adk import VectorMemory
memory = VectorMemory()
```

---

## Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details.

## Related Documentation

- [Workers Guide](../user-guides/workers.md) - Agent execution and orchestration
- [API Reference](../reference/api.md) - Complete API documentation
- [Architecture](../architecture/system-architecture.md) - System architecture

## License

BSD-3-Clause — see [LICENSE](../../LICENSE) for details.

---

**Version**: 0.1.0
**Last Updated**: 2026
