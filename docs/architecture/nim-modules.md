# Nim Powerpack — Native Modules

Aura CLI ships optional native accelerators written in Nim. The base Python
wheel works without any of them; native binaries are used when available and
the system falls back to Python equivalents where that path is implemented.

## Pre-built Binaries

This checkout ships compiled macOS (`macos-x86_64`) binaries in `bin/`. Other
platforms must be built locally.

## Modules

| Binary | Role | Notes |
|--------|------|-------|
| `imagination` | Filesystem scanner | Native accelerator for project indexing |
| `nexus` | Static dependency analyser | Maps import graphs across source files |
| `sentinel` | Real-time file watcher | Content-hash-based change detection |
| `notebook` | Shared memory library (FFI) | Native notebook backend |
| `forge` | Code validator / sanitiser | Validates and sanitises generated code |
| `prism` | Semantic code chunker | Splits source into logical blocks for RAG |
| `aura-monitor` | Terminal content browser | Interactive browser and page-dump tool |

All modules are **optional**. A missing or failed binary causes the system to
use the Python fallback when available, or skip the feature gracefully.

## Building from Source

Requires Nim >= 1.6.0.

```bash
./scripts/build_nim.sh
```

Source code is in `modules_nim/`. Compiled outputs are placed in `bin/`.

## Platform Support

| Platform | Status |
|----------|--------|
| macOS x86_64 | Pre-built binaries included in `bin/` |
| macOS arm64 | Build locally with `./scripts/build_nim.sh` |
| Linux x86_64 | Build locally — not included in checkout |
| Windows | Not currently supported |

## Integration

Each module has a Python bridge in `aura_cli/core/` that locates the binary,
invokes it as a subprocess, and falls back gracefully when it is absent. The
bridge contracts are internal API; the user-facing behaviour is documented in
the relevant tool or feature documentation.

## Performance

Native modules provide measurable speedups for large projects (1,000+ files).
Benchmark locally before making performance claims — gains vary by hardware,
project size, and OS.

---

*Aura CLI — Nim Powerpack reference*
