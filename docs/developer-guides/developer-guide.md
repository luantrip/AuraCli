# Developer Guide — Aura CLI

Complete guide for developers who want to contribute to or extend Aura CLI.

## Table of Contents

- [Getting Started](#getting-started)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Code Patterns](#code-patterns)
- [Adding New Features](#adding-new-features)
- [Testing](#testing)
- [Debugging](#debugging)
- [Contributing](#contributing)

---

## Getting Started

### Prerequisites

- Python 3.10+
- pip
- Git

### Environment Setup

```bash
# Clone the repository
git clone https://github.com/luantrip/AuraCli.git
cd AuraCli

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode with all dev dependencies
pip install -e ".[dev]"

# Run the offline test gate
pytest -q -rs tests/unit tests/e2e --disable-warnings

# Start the CLI
aura
```

### Project Structure

```
AuraCli/
├── aura_cli/
│   ├── cli/              # Rich CLI interface + workers
│   │   ├── workers/      # AGI and Ops workers
│   │   ├── ui/           # UI components
│   │   └── utils/        # Utilities
│   ├── tui/              # Textual TUI (52 widget modules)
│   ├── application/      # Use cases, policies, presentation state
│   ├── core/             # Engine: LLM, agents, tools, memory, sessions
│   └── adk/              # Agent Development Kit (ADK)
├── modules_nim/          # Nim source (native acceleration)
├── bin/                  # Compiled Nim binaries (macOS x86_64 pre-built)
├── extensions/           # Drop-in plugins (*.py)
├── memory/               # Persistent project memory
├── migrations/           # SQL migration files
├── artes/                # Generated ANSI/ASCII art output
├── scripts/              # Build and install scripts
├── tests/                # Unit, e2e, and integration tests
└── docs/                 # Documentation
```

---

## Architecture

### Core Components

1. **Workers**: `AgiWorker` and `OpsWorker` for background operations
2. **Command Processor**: Slash command processing
3. **Function Call Handler**: LLM tool call processing
4. **UI Components**: Rich components for presentation
5. **ADK**: Agent Development Kit — public API for agents and tools

### Data Flow

```
User Input → Command Router → Command Processor / Function Handler → Workers → Results
```

### Threading Model

- Workers run in separate threads
- Queues for thread-safe communication
- Graceful shutdown with timeouts
- Background supervisor for shell processes

For the full architecture, see
[System Architecture](../architecture/system-architecture.md).

---

## Code Patterns

### Type Hints

Always use type hints on public functions:

```python
def process_command(
    command: str,
    stats: StatsTracker,
) -> tuple[bool, str | None]:
    """Process command and return result."""
    ...
```

### Exception Handling

Use specific exceptions from the hierarchy:

```python
from aura_cli.cli.utils.exceptions import ToolExecutionError

try:
    result = tool.execute()
except Exception as e:
    raise ToolExecutionError(
        tool_name="tool_name",
        message=str(e),
        original_error=e,
    ) from e
```

### Logging

Use structured logging with context:

```python
import logging

logger = logging.getLogger(__name__)

logger.info("Processing %s with args %s", tool_name, args)
logger.error("Tool failed: %s", e, exc_info=True)
```

### Imports

- Top-of-file imports where possible
- Use lazy imports only for circular dependencies
- Group imports: stdlib, third-party, local

```python
# Standard library
import os
from pathlib import Path
from typing import Optional

# Third-party
from rich.console import Console

# Local
from aura_cli.core.config import config_manager
```

---

## Adding New Features

### Adding a Slash Command

1. Create a handler in `command_processor.py`:

```python
def handle_new_command() -> None:
    """Handle /new-command."""
    console = Console()
    console.print("New command executed")
```

2. Add routing in `process_slash_command()`:

```python
if command.startswith("/new-command"):
    handle_new_command()
    return True, None, None, None, None
```

3. Add documentation in `handle_help()`:

```python
table.add_row(f"{UIIcons.INFO} /new-command", "Description of the command")
```

### Adding a New Tool

1. Create the tool function in `core/tools/`:

```python
def new_tool(param: str) -> str:
    """New tool description.

    Args:
        param: Parameter description.

    Returns:
        Result description.
    """
    return result
```

2. Register it in `core/tool_registry.py`:

```python
AVAILABLE_TOOLS["new_tool"] = new_tool
```

3. Add tests in `tests/unit/core/test_tools.py`.

---

## Testing

See [Testing Guide](./testing.md) for the full testing reference.

### Quick Reference

```bash
# Offline regression gate (unit + e2e; no network, Docker, or native Nim)
pytest -q -rs tests/unit tests/e2e --disable-warnings

# Run with coverage
pytest tests/unit tests/e2e --cov=aura_cli --cov-report=term-missing

# Lint
ruff check aura_cli tests scripts

# Type check
mypy aura_cli/ --exclude aura_cli/tui/tools
```

---

## Debugging

### Enable Debug Logging

```bash
export AURA_LOG_LEVEL=DEBUG
aura
```

### Python Debugger

```python
import pdb; pdb.set_trace()
```

### Profiling

```bash
python -m cProfile -o profile.stats -m aura_cli.cli.main
```

---

## Contributing

### Process

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Write descriptive commits
4. Add or update tests
5. Run the full validation suite (tests + lint + type check)
6. Open a Pull Request

### PR Checklist

- [ ] Code follows established patterns
- [ ] Tests added/updated
- [ ] All tests pass
- [ ] Documentation updated
- [ ] Type hints added
- [ ] Appropriate exception handling

### Additional Resources

- [API Reference](../reference/api.md)
- [System Architecture](../architecture/system-architecture.md)
- [Testing Guide](./testing.md)
- [CONTRIBUTING](../CONTRIBUTING.md)

---

*Aura CLI — Developer Guide*
