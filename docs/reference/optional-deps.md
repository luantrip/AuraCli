# Optional Dependencies — Aura CLI

This document lists optional dependencies, `pyproject.toml` extras, and
platform-specific behaviour.

---

## Base Installation

```bash
pip install -e .
```

On most environments (Windows, Linux, macOS 11+), pip installs **fastembed**
automatically via an environment marker in `pyproject.toml`
(requires `onnxruntime>=1.17`).

### macOS 10.15 (Catalina) and older hardware

There is **no wheel** for `onnxruntime>=1.17` on Catalina. The marker omits
fastembed during the base install. Aura remains fully functional:

- ChromaDB uses its **default embedding model**
- Advanced vector search with fastembed is disabled until a newer OS or machine is used

Do not run `pip install -e ".[embeddings]"` on Catalina: that extra includes
fastembed without the platform marker and dependency resolution will fail.

---

## Extras

### `dev` — Development

```bash
pip install -e ".[dev]"
```

Installs: pytest, pytest-asyncio, pytest-cov, pytest-xdist, coverage, ruff, mypy

Provides: tests, coverage, lint, formatting, and type checking. Ruff is the
unified lint and format tool; Black, isort, flake8, deptry, and vulture are not
part of this extra.

### `embeddings` — Local Semantic Search

```bash
pip install -e ".[embeddings]"
```

Installs: fastembed, faiss-cpu

Provides: local ONNX embeddings (fastembed) and an optional FAISS backend. Use
on macOS 11+, Windows, or Linux when you want to force the full stack.

**Requirement:** `onnxruntime>=1.17` (not available on macOS 10.15).

### `local-llm` — Local Model Inference

```bash
pip install -e ".[local-llm]"
```

Installs: torch, transformers

### `database-postgresql` — PostgreSQL

```bash
pip install -e ".[database-postgresql]"
```

Installs: psycopg2

### `database-mysql` — MySQL

```bash
pip install -e ".[database-mysql]"
```

Installs: mysql-connector-python

---

## fastembed vs Legacy Documentation

The local embedding stack is **fastembed** (ONNX Runtime), not
`sentence-transformers`. References to sentence-transformers in older docs or
0.3.x installations are obsolete.

---

## Behaviour Without Optional Dependencies

Heavy or platform-specific dependencies use conditional imports. Without
fastembed, Chroma and memory modules degrade to the fallbacks documented in
`aura_cli/core/memory/vector_store.py`.

---

## Verify What Is Installed

```bash
pip show fastembed chromadb aura-cli
python -c "import importlib.util; print('fastembed', bool(importlib.util.find_spec('fastembed')))"
```

---

## Recommendations

| Scenario | Command |
|----------|---------|
| Daily use (macOS 11+, Linux, Windows) | `pip install -e .` |
| Development | `pip install -e ".[dev]"` |
| Vectors + explicit FAISS | `pip install -e ".[embeddings]"` |
| macOS 10.15 Catalina | `pip install -e .` only (no `[embeddings]`) |
| CI | `pip install -e ".[dev]"` |

---

## References

- `pyproject.toml` — `platform_release >= '20'` marker for fastembed
- [Troubleshooting](../user-guides/troubleshooting.md) — Installation issues

---

*Aura CLI — Optional Dependencies — v0.1.0 — 2026*
