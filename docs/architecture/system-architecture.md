# Aura CLI System Architecture

## Overview

Aura CLI is organised as a modular monolith with two interactive adapters, a
public agent SDK, a use-case layer that is independent of concrete infrastructure,
and a broad set of services and integrations in `core`.

```text
                         ┌─────────────────┐
                         │   aura_cli/adk  │  Public API
                         └────────┬────────┘
                                  │ contracts/adapters
┌────────────────┐       ┌────────▼────────┐       ┌────────────────┐
│ aura_cli/cli   │──────▶│   application   │◀──────│ aura_cli/tui   │
│ Typer + Rich   │       │   use cases     │       │   Textual      │
└───────┬────────┘       └────────┬────────┘       └───────┬────────┘
        │                         │                        │
        └─────────────────────────▼────────────────────────┘
                          ┌───────────────┐
                          │     core      │
                          │  domain +     │
                          │ infrastructure│
                          └───────┬───────┘
                                  ▼
                    LLMs, filesystem, Git, Nim,
                    keyring, database, Docker, cloud
```

Central rule enforced by tests: `application` does not import `cli`, `tui`,
`core`, or `adk`. Concrete adapters depend on their contracts and use cases.
`core` still mixes domain and infrastructure; separating them physically is a
direction, not a prerequisite for maintaining current boundaries.

## Layers and Responsibilities

| Layer | Current responsibility |
|---|---|
| `adk/` | Public API for agents, tools, and workflows; late concrete composition |
| `application/` | Use cases, policies, state, contracts, and neutral reducers |
| `core/` | Domain services, providers, persistence, tools, and integrations |
| `cli/` | Typer entry point, composition root, threads, Rich presentation |
| `tui/` | Textual application, widgets, screens, reactive adapters |
| `modules_nim/` | Native acceleration and platform-specific tools |

### Permitted Import Direction

```text
CLI ─┐
TUI ─┼──> Application
Core ┤
ADK ─┘

CLI/TUI composition roots ──> Core concrete services
Core adapters ──────────────> Application ports
```

Imports from `core` into CLI/TUI adapters and cross-imports between CLI and TUI
are prohibited by architectural gates. The TUI still consumes Core services in a
frozen list of composition roots/adapters; new dependencies must use Application
ports. Historical compatibility should be implemented via narrow facades, not by
inverting these dependencies.

## Canonical Flows

### Conversation and function calling

```text
CLI/TUI input
  -> neutral prompt preparation
  -> concrete LLM provider
  -> response classification (Application)
  -> loop budget/state (Application)
  -> ToolExecutionPipeline (Application)
  -> guards and concrete effects (CLI/Core)
  -> history and summarised response (Application)
  -> Rich/Textual presentation
```

`cli.function_call_handler` is a ~388-line adapter today. The duplicated executor
was removed: its facade delegates to the canonical engine in `cli.tool_execution`.
Loop decision, budget, history, messages, and provider failure policy reside in
`application.conversation`.

### Agents and delegation

```text
AppLoop
  -> DelegationService (credential/factory adapter)
  -> DelegationLaunchCoordinator (Application)
  -> AGI/Ops worker + thread
  -> DelegatedTaskRegistry (Application)
  -> typed events
  -> AgentEventStateReducer (Application)
  -> Rich or Textual
```

Handoff preparation, outcomes, registration, reports, and task observation are
isolated behind ports. Threads, keyring, notebook, and concrete factories remain
in the adapters.

### Workspace, session, and memory

`WorkspaceState` is the application facade for conversation state, context,
memory, tangents, and checkpoints. `RuntimeServices` composes the implementations
by resolved root. All persistent artefacts must go through `ArtifactLayout` and
`core.paths`; tests use temporary `AURA_HOME` and `AURA_PROJECT_ROOT` values.

### Events and presentation

`TypedEventBus`, `ReactiveStateStore`, command routing, and reducers live in
`application.presentation`. CLI and TUI convert concrete components into ports
and views. Tool events separate `task_id`, `parent_task_id`, and `execution_id`,
avoiding visual correlation by inference.

## Composition Roots

- `aura_cli.cli.main`: Typer commands and Rich session initialisation
- `aura_cli.cli.runtime.RuntimeServices`: workspace and project services
- `aura_cli.interface_runtime`: interface selection
- `aura_cli.tui.app`: Textual composition
- `aura_cli.core.di_bootstrap`: concrete bindings and container compatibility

Informational commands (`--help`, `--version`) are side-effect free. The Sentinel
check no longer passes `--version` to the legacy binary; the Nim implementation
implements the new contract for future builds.

## Migration Status

Completed:

- P0 security and incorrect behaviour issues
- Canonical authorities for tools, commands, workspace, config, and agents
- Major deduplication removals
- Dependency gates and artefacts
- Cross-cutting extractions from CLI/TUI to Application
- Known stub, productive mock, cache, and accidental artefact cleanup

Still evolving:

- `core` physically mixes domain and infrastructure
- `AuraTUI` remains large (~530 lines), though reducers and routing have been
  extracted
- AGI/Ops workers and some CLI handlers still contain concrete orchestration
- AuraPaint is a native bounded context inside the TUI/Application boundary;
  its document and generation services remain independent of Textual widgets
- ADK/Core compatibility facades remain while legacy consumers exist

## Quality Gates

- Unit tests per use case and adapter
- Integration tests for chat, startup, and bridges
- Architecture tests preventing prohibited dependencies
- `ruff` check and `git diff --check`
- Mandatory artefact isolation in tests
- Artefact tracking in [`generated-artifacts.md`](../reference/generated-artifacts.md)

Historical offline baseline: **4,656 passed** across `tests/unit` and `tests/e2e`.
Platform-specific failures require native Nim binaries, the `aura_cli_nim`
package, or the `fastembed` extra. The gate explicitly excludes `tests/integration`,
real providers, network, Docker, remote Git, and physical terminals.
