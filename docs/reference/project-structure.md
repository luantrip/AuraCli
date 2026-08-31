# Project Structure

Concise reference for the current directory tree. For detailed responsibilities
see the [codebase map](./codebase-map.md).

```text
AuraCli/
├── aura_cli/
│   ├── adk/                 # Public agent SDK
│   ├── application/         # Use cases and neutral contracts
│   │   ├── agents/
│   │   ├── commands/
│   │   ├── conversation/
│   │   ├── editing/
│   │   ├── extensions/
│   │   ├── observability/
│   │   ├── paint/
│   │   ├── presentation/
│   │   ├── refactoring/
│   │   ├── sessions/
│   │   ├── tools/
│   │   └── workspace/
│   ├── core/                # Domain, services, and infrastructure
│   │   ├── evaluation/      # Durable runs, selection, metrics, and reports
│   │   ├── reliability/    # Profiles, retries, idempotency, middleware, faults
│   │   ├── arena/           # Competitive subagent execution
│   │   ├── skills/          # Installed skill lifecycle
│   │   └── mcp/             # MCP adapter and transports
│   ├── cli/                 # Typer/Rich adapter
│   └── tui/                 # Textual adapter
├── modules_nim/             # Nim source (native acceleration)
├── bin/                     # Compiled Nim binaries (macOS x86_64 pre-built)
├── extensions/              # Drop-in plugin files (*.py)
├── memory/                  # Persistent project memory
├── migrations/              # Reserved SQL migrations
├── artes/                   # Paint output files
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── architecture/
│   ├── developer-guides/
│   ├── reference/
│   ├── user-guides/
│   └── internal/
├── scripts/                 # Build, install, and audit scripts
└── pyproject.toml
```

## Generated Directories

These are not source and should remain git-ignored:

- `.aura/` and `.aura_vectors/`
- `.pytest_cache/`, `.ruff_cache/`, and `__pycache__/`
- Logs, coverage outputs, and temporary artefacts
- Build staging and `*.egg-info` metadata

`.venv/` is the local virtual environment and should not be deleted during
routine cleanup. The full inventory of producers and destinations is in
[`generated-artifacts.md`](./generated-artifacts.md).

## Entry Points

| Entry point | Target |
|---|---|
| CLI | `aura_cli.cli.main:app` |
| Interface selection | `aura_cli.interface_runtime` |
| TUI | `aura_cli.tui.app` |
| ADK | facade `aura_cli.adk` |
| Nim build | `scripts/build_nim.sh` |

## Placement Rules

- Reusable decisions testable without infrastructure belong in `application`
- Domain and current technical implementations stay in `core` until explicitly migrated
- Rich/Typer belongs in `cli`; Textual belongs in `tui`
- API intended for external authors belongs in `adk`
- Generated files must never appear as sources under `aura_cli/`

---

*Aura CLI — Project Structure — v0.1.0 — 2026*
