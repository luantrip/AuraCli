---
name: tdd-workflow
description: Use this skill when writing new features, fixing bugs, or refactoring code. Enforces test-driven development with the Red-Green-Refactor cycle and 80%+ coverage using pytest. Covers unit tests, integration tests, mocking, edge cases, and coverage configuration.
version: 1.0.0
author: Aura Core Team
---

# Test-Driven Development Workflow

This skill ensures all code development follows TDD principles with comprehensive test coverage using pytest.

## Core Principles

1. **Tests BEFORE Code** — Always write tests first, then implement.
2. **80%+ Coverage** — Minimum across branches, functions, and lines.
3. **All Test Types** — Unit + Integration + E2E (when applicable).

## The Red-Green-Refactor Cycle

### Step 1: Write the Test First (RED)

```python
# tests/unit/test_search.py
import pytest

def test_search_returns_relevant_results():
    results = search_items("election")
    assert len(results) == 5
    assert "trump" in results[0]["name"].lower()

def test_search_empty_query_raises():
    with pytest.raises(ValueError, match="Query cannot be empty"):
        search_items("")

def test_search_falls_back_when_db_unavailable(mocker):
    mocker.patch("app.db.vector_search", side_effect=Exception("DB down"))
    results = search_items("test")
    assert isinstance(results, list)  # graceful fallback
```

### Step 2: Run Tests (Verify FAIL)
```bash
pytest tests/
# Tests must FAIL — we haven't implemented yet
```

### Step 3: Write Minimal Implementation (GREEN)
```python
def search_items(query: str) -> list[dict]:
    if not query:
        raise ValueError("Query cannot be empty")
    try:
        embedding = generate_embedding(query)
        return vector_search(embedding)
    except Exception:
        return keyword_search(query)
```

### Step 4: Run Tests (Verify PASS)
```bash
pytest tests/
# Tests must PASS now
```

### Step 5: Refactor (IMPROVE)
- Remove duplication
- Improve naming
- Optimize performance
- Keep tests green

### Step 6: Verify Coverage
```bash
pytest --cov=aura_cli --cov-report=term-missing
# Target: 80%+ across all metrics
```

## Test Types

### Unit Tests — Individual functions in isolation

```python
import pytest
from unittest.mock import MagicMock, patch

def test_calculate_similarity_identical():
    embedding = [0.1, 0.2, 0.3]
    assert calculate_similarity(embedding, embedding) == pytest.approx(1.0)

def test_calculate_similarity_orthogonal():
    a, b = [1, 0, 0], [0, 1, 0]
    assert calculate_similarity(a, b) == pytest.approx(0.0)

def test_calculate_similarity_null_raises():
    with pytest.raises(TypeError):
        calculate_similarity(None, [])
```

### Integration Tests — API endpoints and database

```python
import pytest
from app import create_app

@pytest.fixture
def client():
    app = create_app(testing=True)
    return app.test_client()

def test_search_endpoint_returns_200(client):
    response = client.get("/api/search?q=election")
    data = response.get_json()
    assert response.status_code == 200
    assert data["success"] is True
    assert len(data["results"]) > 0

def test_search_missing_query_returns_400(client):
    response = client.get("/api/search")
    assert response.status_code == 400

def test_search_fallback_when_db_down(client, mocker):
    mocker.patch("app.db.vector_search", side_effect=Exception("DB down"))
    response = client.get("/api/search?q=test")
    data = response.get_json()
    assert response.status_code == 200
    assert data.get("fallback") is True
```

## Mocking External Services

### Mock Database
```python
@pytest.fixture
def mock_db(mocker):
    return mocker.patch("app.db.query", return_value=[
        {"id": "1", "name": "Test Item"},
        {"id": "2", "name": "Another Item"},
    ])
```

### Mock External API
```python
@pytest.fixture
def mock_openai(mocker):
    return mocker.patch(
        "app.services.generate_embedding",
        return_value=[0.1] * 1536
    )
```

## Edge Cases to Always Cover

1. **None/empty input**: `None`, `""`, `[]`, `{}`
2. **Invalid types**: pass wrong type, expect TypeError
3. **Boundary values**: min/max integers, empty collections
4. **Error paths**: network failures, DB errors, timeouts
5. **Concurrent operations**: race conditions when relevant
6. **Large data**: performance with 10k+ items

## File Organization

```
aura_cli/
├── core/module.py
└── tests/
    ├── unit/
    │   └── test_module.py       # Pure unit tests
    ├── integration/
    │   └── test_api.py          # API / DB integration
    └── e2e/
        └── test_critical.py    # End-to-end flows
```

## Coverage Configuration

```ini
# pytest.ini
[pytest]
addopts = --cov=aura_cli --cov-report=term-missing

[coverage:report]
fail_under = 80
exclude_lines =
    pragma: no cover
    if TYPE_CHECKING:
    @abstractmethod
```

## Anti-Patterns to Avoid

```python
# ❌ Testing implementation details
assert service._internal_cache_size == 5

# ✅ Test observable behavior
assert response.json()["count"] == 5

# ❌ Tests depend on each other
def test_creates_item(): ...
def test_updates_item(): ...  # depends on previous!

# ✅ Each test is self-contained
def test_updates_item(db):
    item = create_test_item(db)
    # test update logic
```

## Success Metrics

- ✅ All tests passing (green)
- ✅ 80%+ coverage achieved
- ✅ Edge cases covered (None, empty, invalid, error)
- ✅ No shared state between tests
- ✅ External dependencies mocked in unit tests
- ✅ Test names describe the behavior being tested
