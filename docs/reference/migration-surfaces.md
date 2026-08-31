# Migration Surfaces and Re-exports

Inventory of migrated facades and public re-exports, maintained to prevent
transient facades from hardening into permanent architecture.

## Rule

An intermediate module with no behaviour of its own is only kept when it
represents a public API or a stable package boundary. Internal imports and
tests must point to the canonical authority. Preserved re-exports must
describe themselves as API, not as "temporary compatibility".

## Removed During Consolidation

- `aura_cli.core.tools_registry`: manual catalogue with no consumers — removed;
  `core.tool_manifest` is generated metadata and `core.service_registry` is the
  sole runtime authority.
- `aura_cli.core.memory_advanced`: new consumers use `aura_cli.core.semantic`;
  the historical name remains as an implementation and compatibility surface
  during migration, not as a runtime memory store.
- `aura_cli.core.testing.mocking`: removed; had no consumer and its apply method
  was a stub. Use `unittest.mock`/`pytest-mock` in tests.

| Old surface | Current authority |
|---|---|
| Private history helpers in `cli.function_call_handler` | `application.conversation` |
| Builders/supervisor in `cli.delegated_tasks` | `application.agents.delegation` |
| Duplicate builders in `AppLoop` | Delegation service/coordinator |
| Chat wrappers in `tui_session_service` | `application.sessions` |
| `cli.workers.queue_agi_adapter` | `application.agents.queue_event_emitter` |
| `cli.workers.agi_event_adapter` | `application.agents.event_emitter` |
| `tui.routing.settings` | `application.presentation_routing` |
| `tui.commands.slash_commands` | `application.commands` |
| `tui.controller` | `application.presentation.command_routing` |
| AuraPaint engine facades in `tui.tools.paint` | `application.paint` |
| `core.extensions.hooks` | `core.hooks.extension_hooks` |
| Unused imperative functions from `tool_panel_helper` | `tool_panel_context` |
| No-op `_restore_environment` in `OpsWorker` | Removed — worker no longer modifies the environment |
| `tui.utils.file_icons` | `application.file_icons` |
| `show_typing_indicator`/`hide_typing_indicator` aliases | `show_thinking`/`hide_thinking` |
| Dependency re-exports from `cli.app_loop` mixins | Direct imports in consumer handlers |
| `ContextManager` re-export in `cli.main` | Direct use from `core.context.base` |

All productive consumers and tests were migrated before removal.

## Preserved Public Re-exports

| Surface | Reason |
|---|---|
| `aura_cli.adk.workflow` | Documented ADK SDK API |
| `aura_cli.adk.metrics` | Documented ADK observability API |
| `aura_cli.core.extensions.lifecycle` | Public Core subsystem export |
| `aura_cli.core.extensions.registry` | Public Core subsystem export |
| `aura_cli.core.events.agi_events` | Widely consumed contract by Core and integrations |
| `aura_cli.core.events.operational_feedback` | Public operational feedback surface |
| `aura_cli.core.hooks.extension_hooks` | Historical API still consumed by extensions |
| `aura_cli.core.agents.memory_bridge` | Bridge still used by external integrations |
| `TUIEventBus` | TUI-specific public name wrapping `TypedEventBus` |

These modules are not candidates for silent removal. Their removal requires a
deprecation cycle, an external consumer inventory, and a release note.

## Visual Governance

- `WorkItemEnvelope` is the authority for visual lifecycle
- `RealtimeProjectionReducer` is the sole productive entry point for
  `AgiEvent → SurfaceRequest`
- Application, Core AGI runtimes, and workers must not call renderers, console,
  or notifications directly
- Every new `WorkItemKind` must declare lifecycle, surfaces, attention, and
  evidence in `VISUAL_CAPABILITIES`

## ADK Deprecation Policy

Public deprecations are recorded in `aura_cli.adk.DEPRECATIONS` with the
replacement name, initial version, and first major version at which removal
may occur. The symbol must remain resolvable until that version, and each
intermediate release must carry a migration note. Currently `MemoryStore`
points to `PersistentMemory`, was deprecated in 0.2.0, and cannot be removed
before 1.0.0.

## Deliberate Pending Items

- Task mapping belongs only to the registry; tests that need to assemble state
  use the manager's explicit surface, without an alias on `AppLoop`.
- `function_call_handler.execute_tool_call` is a public entry point and test
  patch point, though it delegates to the canonical engine.
- `legacy_stats` names in telemetry payloads are part of the serialised format;
  renaming them requires schema migration, not just textual cleanup.
- ADK ↔ AgentMemory synchronisation represents two genuinely distinct models;
  occurrences of "legacy" there describe format, not a dead facade.
- TUI bridge queue polling is an operational fallback when `SyncManager` fails;
  it has been renamed to reflect its role and must remain covered by tests.

---

*Aura CLI — Migration Surfaces — v0.1.0 — 2026*
