# Contributing to Aura CLI

Thank you for your interest in contributing! This guide will help you get started.

## Development Environment Setup

```bash
# Clone the repository
git clone https://github.com/luantrip/AuraCli.git
cd AuraCli

# Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in development mode with all dev dependencies
pip install -e ".[dev]"
```

### Optional Extras

```bash
pip install -e ".[embeddings]"    # fastembed + faiss (not on macOS 10.15)
pip install -e ".[visualization]" # Plotly + Dash dashboards
```

### Nim Powerpack (optional)

If you need to work on the native binaries:

```bash
./scripts/build_nim.sh
```

## Running Tests

```bash
# Offline regression gate (unit + e2e; no network, Docker or native Nim)
pytest -q -rs tests/unit tests/e2e --disable-warnings

# Run specific test categories
pytest tests/unit/ -q
pytest tests/integration/ -q
pytest tests/e2e/ -q

# Run a specific test file
pytest tests/unit/core/test_di_container.py -q --tb=short

# Run with coverage
pytest tests/unit tests/e2e --cov=aura_cli --cov-report=term-missing
```

> Run tests with the project's virtual environment (`.venv/bin/python -m pytest ...`).
> The shared `conftest.py` sets up mocks and `pytest-timeout`; running outside the
> venv can hang on network I/O or interactive prompts.

## Linting

```bash
# Check for issues
ruff check aura_cli/

# Auto-fix what's possible
ruff check aura_cli/ --fix
```

## Code Style

We use the following tools to enforce consistent style:

- **Ruff** — Linter, formatter and import sorting (line length 88)
- **Type hints** — All public functions must have type annotations (PEP 561)

```bash
# Format code
ruff format aura_cli/ tests/ scripts/

# Type check
mypy aura_cli/ --exclude aura_cli/tui/tools
```

### Conventions

- Use `snake_case` for functions and variables, `PascalCase` for classes.
- Docstrings follow Google style (Args/Returns/Raises sections).
- Keep modules focused — one primary responsibility per file.
- Private methods are prefixed with `_`.

## Pull Request Process

1. **Fork** the repository and create a feature branch:
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Write code** following the style guidelines above.

3. **Add or update tests** for any new functionality or bug fixes.

4. **Run the full validation suite** before submitting:
   ```bash
   pytest -q -rs tests/unit tests/e2e --disable-warnings
   ruff check aura_cli/
   mypy aura_cli/ --exclude aura_cli/tui/tools
   ```

5. **Commit** with a clear, descriptive message:
   ```bash
   git commit -m "feat: add X capability to Y module"
   ```

6. **Push** and open a Pull Request against `main`.

7. **PR description** should include:
   - Summary of what changed and why
   - How to test the changes
   - Any breaking changes or migration notes

## Architecture Overview

The codebase follows a layered architecture:

```
Interfaces (CLI / TUI)
    ↓
Application (use cases and orchestration)
    ↓
Core (LLM, Agents, Tools, Memory)
    ↓
Nim Powerpack (performance-critical native binaries)
```

For the full architecture diagram and detailed documentation, see:
- [architecture/system-architecture.md](architecture/system-architecture.md)
- [reference/project-structure.md](reference/project-structure.md)

## DI Container — Adding New Services

Aura CLI uses a dependency injection container (`aura_cli/core/di.py`) to manage service lifetimes and dependencies. Services are identified by the `Services` enum.

### Registering a new service

```python
from aura_cli.core.di import register, Services, Lifecycle

register(
    Services.MY_SERVICE,
    factory=lambda c: MyService(c.resolve(Services.SOME_DEPENDENCY)),
    lifecycle=Lifecycle.SINGLETON,  # or Lifecycle.TRANSIENT
    dependencies=[Services.SOME_DEPENDENCY],
)
```

The factory receives the container as its first argument when it accepts one, so
dependencies can be resolved lazily and initialization order is derived from the
declared `dependencies`.

### Resolving services

```python
from aura_cli.core.di import resolve, Services

my_service = resolve(Services.MY_SERVICE)
```

### Service lifetimes

| Lifecycle | Behaviour |
|-----------|-----------|
| `SINGLETON` | One instance for the entire application lifetime (created on first resolve) |
| `TRANSIENT` | New instance on every resolve |

When adding a new core service, add its identifier to the `Services` enum, register
it during DI bootstrap (`aura_cli/core/di_bootstrap.py`), and add a unit test in
`tests/unit/core/test_di_container.py`.

## Getting Help

- Open an issue for bugs or feature requests
- Start a discussion for questions or design proposals
- Check existing issues before creating new ones
