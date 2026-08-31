# Application Layer

Live reference for the `aura_cli.application` layer.

## Contract

Application contains business and orchestration decisions that can be exercised
without a terminal, Textual, a real LLM provider, a real filesystem, a keyring,
or a worker thread. Its modules receive data, protocols/callables, and return
value objects, outcomes, events, or explicit state mutations.

Prohibited dependencies within this layer:

- `aura_cli.cli`
- `aura_cli.tui`
- `aura_cli.core`
- `aura_cli.adk`

The consolidated inventory has ~85 Python modules and ~13,900 lines. Paint accounts
for most of the volume; outside the visual sub-application there are approximately
8,300 lines of use cases and contracts.

## Package Map

| Package | Role | Contract/use-case examples |
|---|---|---|
| `agents` | Lifecycle, events, and delegation | Runtime, registry, launcher, reports, feedback, artefact classification |
| `commands` | Neutral catalogue | Command definition, aliases, and resolution |
| `conversation` | LLM turn and history | Prompt, function loop, provider errors, tool summaries |
| `editing` | Code changes | Planning, validation, and history |
| `extensions` | Plugins and hooks | Lifecycle, registry, subprocess contracts, and trust |
| `observability` | Metrics and consumption | Coordinator, snapshots, and token usage |
| `paint` | AuraPaint bounded context | Document, layers, animation, export, and localisation |
| `presentation` | Neutral reactive state | Event bus, state store, reducers, and command routing |
| `refactoring` | Refactoring planning | Plans and pre-execution validation |
| `sessions` | Session use cases | Save/load/list/delete, chat mapping, and context snapshots |
| `tools` | Canonical pipeline | Guards, execution, hooks, and outcomes |
| `workspace` | Aggregated project state | Context, memory, tangents, checkpoints, and consolidation |

Root modules support artefacts, diffs, messages, execution feedback, presentation
routing, and toolkit-independent icons.

## Adopted Patterns

### Explicit Ports

Integrations are callables or small Protocols defined alongside the use case.
Examples: thread observation, snapshot reading, worker factory, task registration,
and event emission. The composition root provides the concrete adapter.

### Outcomes and Value Objects

Expected failures do not depend on UI exceptions. `DelegationLaunchOutcome`,
`ProviderErrorResolution`, plans, snapshots, and immutable states make decisions
testable and preserve visual translation in the adapters.

### Reducers and Stores

Events enter as data; reducers produce state. Rich and Textual observe the result
without duplicating correlation, throttling, or lifecycle rules.

### Correlated Visual Lifecycle

`presentation.work_items` projects turns, operations, and agent events into a
common visual language. `WorkItemEnvelope` preserves session, turn, task,
operation, and execution IDs; describes state, attention, capabilities, and
evidence without depending on Rich or Textual. `TurnExecution` and `AgiEvent`
remain authorities for execution and transport: adapters only produce immutable
snapshots for CLI, TUI, queues, and persistence.

`presentation.lifecycle_audit` verifies complete sequences: a started task must
finish, fail, be cancelled, or remain in an explicit resumable state (approval,
external wait, or interruption). The auditor also rejects terminal events without
a correlated start, enabling temporal lifecycle testing rather than just final
snapshot checks.

### Compatibility Facades

When a historical function must remain importable in CLI/Core, it must be a short
facade that delegates to the use case. The implementation is not copied to
preserve an old API.

## How to Add a Use Case

1. Model input, output, and invariants without importing adapters.
2. Define minimal ports for the required effects.
3. Implement the adapter in CLI, TUI, Core, or ADK.
4. Test the use case with in-memory ports.
5. Test the binding in the adapter.
6. Add or adjust the architectural gate when a new boundary emerges.

Avoid singletons, direct environment variable reads, late UI imports, access to
`Path.cwd()`, and Rich/Textual strings inside Application. Path resolution,
credentials, logging, and process lifecycle belong in composition.

## Planned Work

- Remaining AGI/Ops worker policies
- Remaining lifecycle in CLI handlers
- View models and reducers still embedded in `AuraTUI`
- Future physical separation of domain and infrastructure currently in `core`
- AuraPaint is already the native bounded context for terminal art workflows

---

*Aura CLI — Application Layer — v0.1.0 — 2026*
