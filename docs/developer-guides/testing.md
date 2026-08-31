# Testing Guide — Aura CLI

---

## Overview

The test suite is split into three categories:

| Category | Location | When to run |
|----------|----------|-------------|
| **Unit** | `tests/unit/` | Always — no external dependencies |
| **E2E** | `tests/e2e/` | Always — simulated flows, no real network |
| **Integration** | `tests/integration/` | Explicitly — requires real providers, network, Docker |

The offline gate is `tests/unit` + `tests/e2e`. Integration tests are excluded
from the default run because they require live external services.

---

## Running Tests

### Offline Gate (required before every commit)

```bash
pytest -q -rs tests/unit tests/e2e --disable-warnings
```

The maintained full-suite gate currently reports **4,911 passed**, with no skipped
tests or warnings. The historical offline unit/e2e baseline below remains useful
for comparing older releases and is not the current release count.

### Individual categories

```bash
# Unit tests only
pytest tests/unit/ -q

# E2E tests only
pytest tests/e2e/ -q

# Integration tests (requires live services)
pytest tests/integration/ -q
```

### Single file or test

```bash
pytest tests/unit/core/test_di_container.py -q --tb=short
pytest tests/unit/core/test_di_container.py::TestDIContainer::test_singleton -v
```

### With coverage

```bash
pytest tests/unit tests/e2e \
    --cov=aura_cli \
    --cov-report=term-missing \
    --disable-warnings
```

---

## Linting

```bash
# Check for issues
ruff check aura_cli tests scripts

# Auto-fix what is possible
ruff check aura_cli tests scripts --fix

# Format check
ruff format --check aura_cli tests scripts

# Apply formatting
ruff format aura_cli tests scripts
```

---

## Type Checking

```bash
mypy aura_cli/ --exclude aura_cli/tui/tools
```

---

## Writing Tests

### Structure

```python
"""Tests for module_name."""

import pytest
from unittest.mock import Mock, patch

from aura_cli.core.module import ClassName


class TestClassName:
    """Tests for ClassName."""

    def test_basic_behaviour(self) -> None:
        """Describe what this test verifies."""
        # Arrange
        obj = ClassName(param="value")

        # Act
        result = obj.method()

        # Assert
        assert result == expected_value
```

### Key conventions

- Test files follow `test_<module>.py` naming.
- Test classes follow `TestClassName` naming.
- Each test method has a docstring explaining what it verifies.
- Use `tmp_path` (pytest fixture) or `AURA_HOME`/`AURA_PROJECT_ROOT` env vars
  for any filesystem artefacts — never write to the real `~/.aura/`.
- Mock external providers and network calls in unit tests.
- Integration tests may use real providers; gate them with `pytest.mark.integration`.

### Artefact isolation

Tests that produce files must clean up after themselves or use `tmp_path`. The
CI gate checks that no stale artefacts are left in the working tree.

---

## Platform-Specific Failures

The offline gate may show up to 11 platform-specific failures on environments
that lack:

- Native Nim binaries built for the host platform
- The `aura_cli_nim` package
- The `fastembed` extra (unavailable on macOS 10.15 Catalina)

These are environmental, not regressions. The baseline count excludes them.

---

## Related Documentation

- [Developer Guide](./developer-guide.md) — Project setup and code patterns
- [CONTRIBUTING](../CONTRIBUTING.md) — Pull request process

---

**Version**: 0.1.0
**Last Updated**: 2026
