# Plugin Development Guide

## Overview

Aura CLI supports extensibility through plugins, custom tools, skills, and agents. This guide covers how to extend Aura's capabilities.

## Extension Types

### 1. Custom Skills

Skills are markdown files that provide knowledge to the LLM. They're retrieved using semantic search (RAG).

#### Location
```
aura_cli/consciousness/skills/your-skill.md
```

#### Structure
```markdown
---
name: Your Skill Name
description: Detailed description of when this skill should be used. Include keywords and scenarios.
version: 1.0.0
author: Your Name
---

# Skill Title

## Section 1
Content explaining the topic...

## Section 2
More detailed information...

### Code Examples
```python
example_code()
```
```

#### Best Practices

1. **Description is Critical**: The description is used for semantic matching. Include all relevant keywords and scenarios.

2. **Be Comprehensive**: Include complete information the LLM needs.

3. **Use Examples**: Code examples help the LLM provide accurate responses.

4. **Version Your Skills**: Update version when content changes significantly.

---

### 2. Custom Agents

Agents are specialist personas that can be invoked for specific tasks.

#### Location
```
aura_cli/consciousness/agents/your-agent.md
```

#### Structure
```markdown
---
name: your-agent-name
description: When to use this agent and what it does.
model: sonnet
allowed-tools: Read, Write, Grep
---

You are a [specialist role]. Your task is to [main objective].

## Process

1. **Step One**: What to do first
2. **Step Two**: Next action
3. **Step Three**: Final step

## Constraints

- What NOT to do
- Limits and boundaries

## Output Format

Describe expected output structure...

```json
{
  "field": "value"
}
```
```

#### Configuration Fields

| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Unique agent identifier |
| `description` | string | When to use this agent |
| `model` | string | LLM model: sonnet, opus, haiku |
| `allowed-tools` | string/list | Tools the agent can use |

---

### 3. Custom Tools

Register new tools with the ServiceRegistry.

#### Creating a Tool

```python
# aura_cli/core/tools/my_tools.py

from typing import Any, Dict

def my_custom_tool(param1: str, param2: int = 10) -> Dict[str, Any]:
    """
    Description of what this tool does.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Dictionary with result data
    """
    # Implementation
    result = do_something(param1, param2)
    
    return {
        "success": True,
        "data": result
    }
```

#### Registering the Tool

```python
# In service_registry.py or via plugin

from aura_cli.core.service_registry import get_service_registry, ToolCategory

registry = get_service_registry()
registry._register_tool(
    name="my_custom_tool",
    category=ToolCategory.DEVELOPMENT,
    description="What this tool does",
    function=my_custom_tool,
    schema={
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
            "param2": {"type": "integer", "default": 10}
        },
        "required": ["param1"]
    }
)
```

---

### 4. Plugin System

Use the extension system for more complex plugins.

#### Plugin Structure

```
my_plugin/
├── __init__.py
├── plugin.json
├── tools/
│   └── my_tools.py
├── skills/
│   └── my_skill.md
└── agents/
    └── my_agent.md
```

#### plugin.json

```json
{
  "name": "my-plugin",
  "version": "1.0.0",
  "description": "Plugin description",
  "author": "Your Name",
  "entry_point": "my_plugin:register",
  "dependencies": [],
  "tools": ["my_custom_tool"],
  "skills": ["my_skill"],
  "agents": ["my_agent"]
}
```

#### Plugin Entry Point

```python
# my_plugin/__init__.py

from aura_cli.core.extensions.plugin_api import PluginContext

# NOTE: PluginContext API is experimental and subject to change between
# releases. Pin your Aura CLI version when depending on it.

def register(context: PluginContext):
    """Called when plugin is loaded."""

    # Register tools
    context.register_tool(
        name="my_tool",
        function=my_tool_function,
        category="development",
        description="Tool description",
    )

    # Register hooks
    context.register_hook("pre_tool_use", my_hook_function)

    # Access services (internal API — subject to change)
    registry = context.get_service("registry")
    config = context.get_config()

def my_hook_function(event_data):
    """Hook called before tool execution."""
    tool_name = event_data.get("tool_name")
    # Custom logic
    return event_data  # or modified data
```

---

## Hooks System

### Available Hooks

| Hook | Trigger | Data |
|------|---------|------|
| `pre_tool_use` | Before tool execution | tool_name, args |
| `post_tool_use` | After tool execution | tool_name, result |
| `pre_llm_call` | Before LLM query | prompt, model |
| `post_llm_call` | After LLM response | response, tokens |
| `on_session_start` | Session begins | session_id |
| `on_session_end` | Session ends | session_id, stats |

### Registering Hooks

```python
from aura_cli.core.extensions.hooks import register_hook

@register_hook("pre_tool_use")
def validate_tool_call(event):
    """Validate tool calls before execution."""
    if event["tool_name"] == "dangerous_tool":
        raise PermissionError("Tool not allowed")
    return event

@register_hook("post_llm_call")
def log_token_usage(event):
    """Log token usage after LLM calls."""
    logger.info(f"Tokens used: {event['tokens']}")
    return event
```

---

## TUI Widgets

### Creating Custom Widgets

```python
from textual.widgets import Static
from textual.reactive import reactive

class MyWidget(Static):
    """Custom TUI widget."""
    
    value = reactive("")
    
    def __init__(self, initial_value: str = ""):
        super().__init__()
        self.value = initial_value
    
    def watch_value(self, new_value: str):
        """React to value changes."""
        self.update(f"Value: {new_value}")
    
    def on_mount(self):
        """Called when widget is mounted."""
        self.set_interval(1.0, self.refresh_data)
    
    def refresh_data(self):
        """Periodic refresh."""
        # Update logic
        pass
```

### Integrating with SyncStore

```python
from aura_cli.tui.core.sync_store import get_store

class DataWidget(Static):
    def on_mount(self):
        store = get_store()
        self._unsub = store.subscribe("my.data.path", self.on_data_change)
    
    def on_unmount(self):
        if self._unsub:
            self._unsub()
    
    def on_data_change(self, path: str, value):
        self.update(str(value))
```

---

## Best Practices

### 1. Error Handling

Use structured exceptions:

```python
from aura_cli.core.exceptions import ToolExecutionError

def my_tool(path: str):
    try:
        # operation
    except FileNotFoundError as e:
        raise ToolExecutionError(
            tool_name="my_tool",
            message=f"File not found: {path}",
            args={"path": path}
        )
```

### 2. Logging

Use the standard logger:

```python
from aura_cli.core.logger import get_logger

logger = get_logger(__name__)

logger.debug("Debug info")
logger.info("Info message")
logger.warning("Warning")
logger.error("Error occurred")
```

### 3. Configuration

Use Pydantic for config:

```python
from pydantic import BaseModel, Field

class MyPluginConfig(BaseModel):
    enabled: bool = True
    max_retries: int = Field(default=3, ge=1, le=10)
    api_url: str = "https://api.example.com"
```

### 4. Testing

Write tests for your extensions:

```python
import pytest
from my_plugin import my_tool

def test_my_tool_success():
    result = my_tool("valid_input")
    assert result["success"] is True

def test_my_tool_error():
    with pytest.raises(ToolExecutionError):
        my_tool("invalid_input")
```

---

## Debugging

### Enable Debug Logging

```bash
export AURA_LOG_LEVEL=DEBUG
aura
```

### Inspect Events

```python
from aura_cli.tui.core.sync_store import get_store

store = get_store()
store.subscribe("", lambda p, v: print(f"Event: {p} = {v}"))
```

### Test Skills Matching

```python
from aura_cli.consciousness import get_skill_retriever

retriever = get_skill_retriever()
matches = retriever.find_all_matches("your query", limit=5)
for m in matches:
    print(f"{m.skill.name}: {m.score:.2f}")
```

---

> **Drop-in plugins:** The `extensions/` directory at the project root is the
> intended location for drop-in plugin files (`*.py`). Files placed there are
> loaded automatically at startup without requiring a `plugin.json` manifest.
> For structured plugins with dependencies and skills, use the full plugin
> package structure described above.

---

*Aura CLI — Plugins Guide*
