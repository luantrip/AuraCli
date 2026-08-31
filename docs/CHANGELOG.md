# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased] — offline-first consolidation — 2026-08-28

### LLM providers

- Added native GroqCloud support with `GROQ_API_KEY`, GPT OSS model catalog entries,
  free-tier rate limits, validation, fallback routing, CLI/TUI configuration, and
  readiness coverage.

### Security and workspace

- Strengthened fail-closed policy for confirmation, audit, credentials, and shell.
- Unified workspace root across CLI, TUI, memory, sessions, checkpoints, discovery,
  and task parameters.
- Relative paths, external absolute paths, and symlinks that escape the workspace
  are rejected by workspace-scoped contracts.
- Shell execution runs without `shell=True`, with timeout, isolated process group,
  output limit, and a background supervisor with PID/status/cancel.

### Persistence and workflows

- Rules, snapshots, notebook, checksums, sessions, and vector indexes received
  atomic persistence/locking where applicable.
- Workflows with possible side effects no longer silently fall back to chat; they
  terminate in reconciliation when the effect is uncertain.
- Delegation, outcomes, and terminal events became idempotent with a defensive
  public view, retaining the legacy CLI adapter.

### Documentation and repository

- Documentation reorganised: guides, architecture, and reference maintained as
  canonical content; historical studies and audits removed from the public path.
- `docs/README.md` index revalidated by `scripts/check_docs.py` with no broken
  links.
- Project and module READMEs revised to reflect the current state (counts, module
  names, test and lint commands).
- Linux Nim binaries removed from the checkout; `bin/` retains only the macOS
  target.

### Quality and packaging

- Offline regression: **4,656 passed** in `tests/unit` and `tests/e2e`; remaining
  failures are platform-specific (native Nim, `aura_cli_nim`, and the `fastembed`
  extra, unavailable on macOS 10.15).
- Ruff check/format, Python compilation, mypy on 661 files, and `pip check` passed.
- Base wheel `aura_cli-0.1.0-py3-none-any.whl` built and validated without Nim;
  `aura --version` passed in an isolated environment.
- `deptry` ran with no unused dependencies (one internal `extensions/` plugin
  appears as a false positive).

## [0.1.0] — 2026-06-29

### Added

- Dependency injection system (`core/di`)
- Auto-healing agent with intelligent retry
- Task router for automatic LLM model selection
- Isolated execution context (sandboxing)
- Design patterns library (SingletonMeta, LockPool, handle_exceptions)
- Persistent command history across sessions
- 6 native Nim binaries (imagination, nexus, sentinel, notebook, forge, prism)
- Nim-based terminal browser (`aura-monitor`)
- MC-style dual-pane File Manager with 67 file-type icons
- AuraPaint (native ANSI art editor) with layers, animation, and AI agent
- Memory system with vector search
- 7 LLM providers: Google, Cerebras, OpenRouter, OpenAI, Anthropic, NVIDIA, GroqCloud
- Automatic provider fallback when rate-limited
- AGI mode (`/agi`) for autonomous task execution
- DevOps agent (`/ops`) for git, docker, CI/CD
- Checkpoint and tangent branch system
- Extensible tool catalogue (fs, git, shell, web, docker, k8s)

### Changed

- AppLoop decomposition with LLMQueryMixin extraction (−25% LOC)
- Visual consistency with UIIcons and UIStyles
- Dead code removal via static analysis

### Fixed

- Race conditions in concurrent access
- Socket leaks in network operations
- Memory leaks from circular references
- DoS protection with rate limiting
- Prompt injection sanitisation

### Metrics

- Tests: 4,945 passed (offline gate, macOS; 11 platform-specific failures
  requiring native Nim, `aura_cli_nim`, or `fastembed`)
- Ruff warnings: 0
