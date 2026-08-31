# Codebase Map

Physical and conceptual map of the Aura CLI codebase.

## Root

| Path | Role | Status |
|---|---|---|
| `aura_cli/` | Python product | canonical |
| `modules_nim/` | Native module sources | canonical |
| `bin/` | Native binaries (macOS x86_64 pre-built) | generated/versioned |
| `tests/` | Unit, integration, and E2E tests | canonical |
| `docs/` | Public and internal documentation | canonical |
| `scripts/` | Build, install, and audit scripts | canonical |
| `extensions/` | Trusted Python extensions (drop-in) | extension |
| `memory/` | Project constitution/scratchpad | intentional persistence |
| `migrations/` | Reserved SQL migrations | reserved |
| `artes/` | Paint outputs | generated |
| `.aura/`, `.aura_vectors/` | Local runtime state | generated; absent in a clean checkout |

## Python Package

| Area | Responsibility | Architectural status |
|---|---|---|
| `adk/` | Public agent/tools/workflow SDK | Preserved public boundary |
| `application/` | Use cases and neutral contracts | Canonical layer |
| `core/` | Domain, services, and infrastructure | Functional, still mixed |
| `cli/` | Typer, Rich, threads, and composition | Primary adapter |
| `tui/` | Textual, widgets, screens, and sub-applications | Primary adapter |

## Application Layer

| Package | Responsibility |
|---|---|
| `agents/` | Contracts, runtime, events, delegation, and task management |
| `commands/` | Neutral command catalogue and resolution |
| `conversation/` | Prompt, history, tool loop, and provider failure policy |
| `editing/` | Edit history, planning, and validation |
| `extensions/` | Lifecycle, hooks, plugins, and sub-processes |
| `observability/` | Metrics, coordination, and token tracking |
| `paint/` | Textual-independent AuraPaint engine |
| `presentation/` | Event bus, store, reducers, and routing |
| `refactoring/` | Neutral refactoring planning |
| `sessions/` | Use cases and chat mapping |
| `tools/` | Canonical protected execution pipeline |
| `workspace/` | State, memory, context, tangents, and checkpoints |

Details and rules: [`application-layer.md`](../architecture/application-layer.md).

## Core Layer

| Group | Key directories/modules |
|---|---|
| Agents/AGI | `agents/`, `agi/`, `personas/`, `workflows/` |
| Knowledge | `memory/`, `context/`, `embeddings/`, `sessions/`, `todo/` |
| Engineering | `tools/`, `edit/`, `quality/`, `refactoring/`, `testing/` |
| Integrations | `llm/`, `ops_tools/`, `extensions/`, `hooks/`, `communication/` |
| Composition | `di.py`, `di_bootstrap.py`, `service_registry.py`, `tool_manifest.py` |
| Runtime | `config.py`, `secure_config.py`, `paths.py`, `logger.py`, `stats.py` |
| Native | `nim_runtime.py`, `nim_integrity.py` |

## CLI Layer

| Area | Current responsibility |
|---|---|
| `main.py` | Typer entry point and composition root |
| `runtime.py` | Workspace services per root |
| `app_loop.py` | Interactive controller (~533 lines) |
| `function_call_handler.py` | LLM/tools turn adapter (~388 lines) |
| `tool_execution.py` | Concrete execution, guards, and Rich UI |
| `delegation_service.py` | Credentials and worker factories |
| `delegated_tasks.py` | Thread/notebook adapters (~268 lines) |
| `commands/` | Rich handlers for use cases |
| `workers/` | AGI/Ops, threading, and event adapters |
| `ui/` | Components, rendering, themes, and Rich input |

## TUI Layer

| Area | Current responsibility |
|---|---|
| `app.py` | Main Textual composition (~530 lines) |
| `application.presentation.command_routing` | Neutral controller consumed directly by TUI |
| `core/` | Reactive state synchronisation and adapters |
| `widgets/`, `screens/` | Textual presentation |
| `services/` | TUI session and snapshots |
| `plugins/` | Extension visual adapters |
| `tools/` | Embedded AuraPaint, Monitor, and File Manager |

## Native Modules

| Source | Function |
|---|---|
| `imagination.nim` | Filesystem scanner |
| `nexus.nim` | Dependency graph |
| `sentinel.nim` | Filesystem change detection and incremental state |
| `prism.nim` | Code chunking |
| `forge.nim` | Validation and sanitisation |
| `monitor/` | HTML/ANSI/Markdown terminal browser |
| `notebook/` | Shared notebook library |

## Tests and Boundaries

- `tests/unit/application` — use cases without infrastructure
- `tests/unit/cli` and `tests/unit/tui` — adapters and presentation
- `tests/unit/core` — domain and integrations
- `tests/integration` — wiring, startup, chat, and bridges
- `tests/e2e` — complete behaviour
- `tests/unit/test_architecture_contracts.py` — permitted dependency directions
- `tests/unit/test_module_contracts.py` — public surfaces and compatibility

The inventory of preserved re-exports and removed transient modules is in
[`migration-surfaces.md`](./migration-surfaces.md).

---

*Aura CLI — Codebase Map — v0.1.0 — 2026*
