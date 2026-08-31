# Aura generated artifacts

This document is the source of truth for directories and files created by Aura CLI and its quality tests.

## Storage roots

| Root | Purpose | Lifetime | Policy |
|---|---|---|---|
| `$AURA_HOME` | User-level configuration, logs, caches, memory and sessions | Persistent | Defaults to `~/.aura`; tests must override it |
| `<project>/.aura` | Project notebook, context, checkpoints and operational state | Project-local | Override the project root with `$AURA_PROJECT_ROOT` during tests |
| `<repo>/.venv` | Editable development installation | Rebuildable | Created only by the installer |
| System temporary directory | Test isolation and audit reports | Disposable | Preferred for E2E and quality runs |

## Expected `$AURA_HOME` contents

| Path | Producer | Content |
|---|---|---|
| `config.json` | configuration services and first-run wizard | User configuration; may reference credentials |
| `logs/` | `aura_cli.core.logger` | Rotating application logs |
| `cache/` | persistent and TUI caches | Rebuildable cached data |
| `embeddings_cache/` | embedding cache | Rebuildable vector inputs |
| `vector_db/` | vector-store backends | Persistent vector index |
| `aura_data.db` | persistent memory/database tools | SQLite application data |
| `project_memories/` | unified memory service | Per-project notebooks, scratchpads and sessions |
| `sessions/<session_id>.json` | canonical turn repository, session manager and browser | Schema-versioned, atomically replaced conversation plus operational ledger |
| `model_preferences/preferences.json` | verified model-outcome learner | Bounded global routing decisions and scores; never project state |
| `workflows/` | workflow manager | User-defined workflows |
| `metrics/` | agent metrics | Runtime measurements |
| `extensions/` | extension loader | User-installed extensions |
| `paint/` | Paint recent-files service | Paint preferences and history |
| `snippets.json` | snippet manager | User-defined snippets |
| `.aura_history` | CLI input | Command history |
| `embeddings_venv/` | optional embedding server | Dedicated Python environment |

Immediately after a clean installation and `aura --version`, the observed baseline is `config.json` plus `logs/aura_<date>.log` (about 8 KB total). No `.aura_vectors` directory is expected.

## Expected project `.aura` contents

Known producers may create `notebooks/`, `contexts/`, `backups/`, `checkpoints/`,
`response_cache/`, `agent_memory/`, `vector_db/`, `sentinel_state.json` and
`to-do.md`. Notebook session directories are lazy and must contain at least one
validated page. Model preferences belong only to `$AURA_HOME`. A test that
creates a project artifact must use a temporary project root or remove it
afterwards.

`.aura_history` is intentionally input-only shell history. Full restoration and
auditing use `sessions/<session_id>.json`; the legacy SQLite `conversations`
table is not an authority and must not receive new chat writes.

Python bytecode (`__pycache__`), `.DS_Store`, `.pytest_cache`, coverage files and
local test databases are external runtime/tool artifacts rather than Aura domain
state. Tracked E2E commands isolate their roots and clean these recoverable
outputs after reporting them.

## Monitored quality execution

Run any command through the tracker:

```bash
.venv/bin/python scripts/track_generated_artifacts.py -- .venv/bin/pytest -q
```

The tracker:

1. creates an isolated temporary `AURA_HOME`;
2. snapshots the repository and isolated data directory;
3. runs the requested command;
4. writes `artifact-report.json` with created, modified and deleted paths plus hashes and sizes;
5. returns the wrapped command's exit status.

Use `--output <directory>` to retain a report in a known location. Reports may contain filenames and operational metadata and should be reviewed before publication.

The initial monitored E2E run completed with 45 passing tests. It created `.pytest_cache/` in the repository and `aura_data.db`, `config.json` and the daily log under the isolated `AURA_HOME`; all were removed after inspection.

### Resolved artifact incidents

- A root-level file named `.gz` was traced to `test_backup_postgresql_exception`: the test called the private PostgreSQL backup method with an empty output path, which became `.gz` before the mocked subprocess failed. Backup methods now reject empty output paths and remove partial files after command errors or exceptions; the test uses `tmp_path`. The monitored regression run passed 17 tests and did not recreate `.gz`.

## Installation notes

- `scripts/install_aura_cli.sh` resolves its root from its own location and installs the `dev` extra.
- On macOS Catalina (`Darwin < 20`), `grpcio` is constrained below 1.70 because newer releases do not provide a compatible wheel and otherwise trigger a long source build.
- The shell installer block must contain the repository's absolute current path.

## Quality gates

- E2E and quality tests must run with an isolated `AURA_HOME`.
- Tests must also isolate project artifacts through `AURA_PROJECT_ROOT`.
- No test may write to the real `~/.aura`.
- No test may leave `.aura`, caches, logs, databases or coverage output in the repository root.
- Any newly observed artifact must be assigned a producer, lifetime and cleanup policy in this document.
- Installation checks must verify both the executable path and the shell block.
