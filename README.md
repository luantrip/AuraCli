# Aura CLI

```
        ▄▀█ █░█ █▀█ ▄▀█    █▀▀ █░░ █
        █▀█ █▄█ █▀▄ █▀█    █▄▄ █▄▄ █
```

**AI-powered code assistant with integrated development tools.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python)](https://www.python.org/)
[![Version](https://img.shields.io/badge/Version-0.1.0-blue?style=flat-square)](https://github.com/luantrip/AuraCli/releases)
[![License](https://img.shields.io/badge/License-BSD--3--Clause-green?style=flat-square)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-regression%20gate-brightgreen?style=flat-square)]()
[![Typing](https://img.shields.io/badge/Typing-PEP%20561-blue?style=flat-square)](https://peps.python.org/pep-0561/)

---

## What is Aura CLI?

Aura CLI combines LLMs with a catalog of development tools to automate programming tasks directly from the terminal. It offers two interfaces: a Rich-based CLI and a Textual TUI. The catalog is intentionally extensible, so documentation avoids treating a source-file count as a stable public API.

**Key capabilities:**
- 🤖 **AGI Mode** — Autonomous project manager that plans, executes, and validates multi-step tasks
- 🔧 **DevOps Agent** — Git, Docker, CI/CD, security scanning, infrastructure management
- 📝 **Smart Editing** — Code refactoring, file operations with diffs and rollback
- 🧠 **Memory System** — Persistent memory with vector search across sessions
- 🏟️ **Agent Arena** — Competing subagents with strategy cards and rubric-based selection
- 🔌 **MCP Server** — Expose approved Aura tools over stdio, HTTP, and SSE
- 🧩 **Skills** — Install, validate, search, and package `.aura-skill` extensions
- 🛡️ **Reliability** — Resumable runs, retries, idempotency, isolated profiles, and fault testing
- ⚡ **Nim Powerpack (optional)** — native accelerators for selected filesystem, notebook and code-analysis paths when built locally
- 🎨 **Embedded Tools** — AuraPaint nativo, file manager e terminal browser

---

## Quick Start

```bash
git clone https://github.com/luantrip/AuraCli.git
cd AuraCli
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
./scripts/install_aura_cli.sh   # configura PATH no shell (~/.zshrc)
aura
```

On first run, configure an API key:
```
› /settings   # configure API keys
› /model      # select model
```

### Supported Providers

| Provider | Example Models | Cost |
|----------|---------------|------|
| **Google Gemini** | `gemini-2.5-flash` (default), `gemini-2.5-pro` | Free tier available |
| **Cerebras** | `gpt-oss-120b`, `zai-glm-4.7`, `llama3.1-8b` | Free tier available |
| **OpenRouter** | `openrouter/free`, Nemotron 3 Super/Ultra, Qwen 3 Coder | Free models available |
| **NVIDIA** | `nvidia/nemotron-3.5-lightning-30b-a3b`, Nemotron 3 Super/Ultra | Hosted API |
| **Groq** | `openai/gpt-oss-20b`, `openai/gpt-oss-120b` | Free tier available |
| **OpenAI** | `gpt-4o`, `gpt-4o-mini` | Paid |
| **Anthropic** | `claude-sonnet-4-6` | Paid |

> **Recommended:** Configure Google + Cerebras + OpenRouter + Groq (free tiers) for uninterrupted AGI pipeline execution with automatic fallback when rate-limited.

---

## Usage

```bash
# Natural language chat
› Read main.py and explain the architecture

# AGI — autonomous multi-step execution
› /agi create a REST API with FastAPI and PostgreSQL

# DevOps
› /ops git commit the current changes
› /ops docker ps
› /arena --quick propose a robust implementation
› /skill list
› /mcp status

# Direct shell passthrough
› ls -la
› grep -r "TODO" .

# Theme (auto-detects OS dark/light mode)
› /theme auto
```

Retomar uma sessão por identificador, prefixo ou nome:

```bash
aura --resume 01a1633f-9540-7a92-b64a-e619e592a625
```

### Slash Commands

| Command | Description |
|---------|-------------|
| `/agi [goal]` | Autonomous AGI project manager |
| `/ops [mode] <task>` | DevOps agent (git / docker / general) |
| `/arena [options] <task>` | Compete subagents and select the strongest result |
| `/skill <subcommand>` | Manage installed skills (`list`, `install`, `pack`, `search`) |
| `/mcp <subcommand>` | Inspect or start the MCP server |
| `/tui` | Launch graphical TUI |
| `/tools` | List all available tools |
| `/session [save\|load\|list]` | Session management |
| `/resume <id\|prefix\|name>` | Restore a local or imported session |
| `/theme [name]` | Switch theme |
| `/checkpoint [cmd]` | Git project snapshots |
| `/tangent` | Conversation branching |
| `/init` | Index current project |
| `/help` | All commands |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                    Interfaces                         │
│  ┌──────────────────┐  ┌─────────────────────────┐  │
│  │   CLI (Rich)     │  │     TUI (Textual)       │  │
│  │  app_loop.py     │  │  app.py + widgets       │  │
│  │  command_router  │  │  screens, event bridge  │  │
│  └────────┬─────────┘  └───────────┬─────────────┘  │
│           └──────────┬──────────────┘                │
├──────────────────────┼───────────────────────────────┤
│                Application Layer                     │
│  use cases · presentation policies · execution       │
│  sessions · workspace · agents · AuraPaint domain    │
├──────────────────────┼───────────────────────────────┤
│                  Core Engine                          │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │   LLM   │  │  Agents  │  │   Tools catalog    │  │
│  │ litellm │  │  AGI/Ops │  │ fs, git, shell,    │  │
│  │ fallback│  │ personas │  │ web, docker, k8s   │  │
│  └─────────┘  └──────────┘  └────────────────────┘  │
│  ┌─────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Memory  │  │ Context  │  │   Sessions         │  │
│  │ fastemb │  │ indexer  │  │ checkpoint/tangent  │  │
│  └─────────┘  └──────────┘  └────────────────────┘  │
├──────────────────────────────────────────────────────┤
│              Nim Powerpack (optional)                 │
│  imagination · nexus · sentinel · forge · prism      │
│  aura-monitor · notebook                             │
└──────────────────────────────────────────────────────┘
```

Full architecture: [docs/architecture/system-architecture.md](docs/architecture/system-architecture.md)

---

## Nim Powerpack

The Nim Powerpack is optional and is not required by the base Python wheel. This checkout ships compiled macOS (`macos-x86_64`) binaries in `bin/`; other targets must be built locally. Build and benchmark it locally before making performance claims:

| Binary | Function | Benefit |
|--------|----------|---------|
| `imagination` | Filesystem scanner | Optional native accelerator; benchmark locally |
| `nexus` | Static dependency analyzer | Optional native accelerator |
| `sentinel` | Real-time file watcher | Optional native watcher |
| `notebook` | Shared memory library (FFI) | Optional native notebook backend |
| `forge` | Code validator/sanitizer | Optional native validator |
| `prism` | Semantic code chunker | Optional native chunker |
| `aura-monitor` | Terminal content browser | Optional native monitor |

Build from source (requires Nim >= 1.6.0):
```bash
./scripts/build_nim.sh
```

---

## Agent Reliability

The native evaluation layer provides durable run scheduling and resume, blind
candidate selection, quality/diversity reports, retry with backoff, idempotent
operations, isolated credential profiles, middleware, and deterministic fault
injection. Arena evaluations write JSON and Markdown reports next to the run
artifacts.

MCP exposes read-only tools by default. Write access requires an explicit CLI
flag, and destructive operations remain governed by the existing tool policies.

See [Evaluation and Reliability](docs/reference/evaluation-and-reliability.md)
for the public contracts and operational examples.

## Optional Extras

```bash
pip install -e ".[dev]"                # pytest, ruff, mypy, black
pip install -e ".[embeddings]"         # fastembed + faiss (local ONNX embeddings)
pip install -e ".[local-llm]"          # torch + transformers (local models)
pip install -e ".[database-postgresql]"  # psycopg2 for PostgreSQL tools
pip install -e ".[database-mysql]"     # mysql-connector for MySQL tools
```

> **macOS 10.15 Catalina:** Use base install only — `onnxruntime` has no Catalina wheel. Semantic search still works via fastembed's fallback to keyword-based search.

---

## Development

```bash
pip install -e ".[dev]"

# Full regression gate
# Run the current regression gate locally; counts vary as tests evolve.
pytest -q

# Lint
ruff check aura_cli tests scripts
ruff format --check aura_cli tests scripts

# Type check
mypy aura_cli/ --exclude aura_cli/tui/tools

# Format
ruff format aura_cli tests scripts
```

---

## Project Structure

```
AuraCli/
├── aura_cli/           Python source
│   ├── cli/            Rich CLI interface + workers
│   ├── tui/            Textual TUI (consulte `aura_cli/tui/README.md`)
│   ├── application/    Use cases, policies and presentation state
│   ├── core/           Engine: LLM, agents, evaluation, reliability, tools, memory, sessions
│   └── adk/            Agent Development Kit (ADK)
├── modules_nim/        Nim source (F1 Engine)
├── bin/                Compiled Nim binaries
├── extensions/         Drop-in plugins (*.py)
├── memory/             Persistent project memory (constitution, scratchpad)
├── migrations/         SQL migration files (for DB ops tools)
├── artes/              Generated ANSI/ASCII art output
├── scripts/            Build and install scripts
├── tests/              Unit, e2e and integration contracts (counts are dated below)
└── docs/               Architecture, guides and reference material
```

Full structure: [docs/reference/project-structure.md](docs/reference/project-structure.md)

---

## Security

- API keys use the OS keyring by default. If secure storage is unavailable, the configuration path fails closed instead of silently writing plaintext; insecure storage requires an explicit opt-in.
- Confirmation is contextual rather than universal: auto-run can skip prompts only where the current policy permits it. Unknown policy, unavailable confirmation and risky operations fail closed.
- File-edit operations that support backups create them before mutation. Internal rules, snapshots, sessions and notebook metadata use atomic persistence/checksum contracts; these are separate guarantees from edit backups.
- File and memory paths are resolved against the canonical workspace. Relative traversal, external absolute paths and symlinks that resolve outside the workspace are rejected by the relevant contracts.
- Multi-layer code validation and the integrated vulnerability scanner remain available under `core/ops_tools/security/`.

### Offline validation and limitations

The offline gate runs across `tests/unit` and `tests/e2e`. It deliberately excludes `tests/integration`, real providers, network calls, Docker, remote Git, physical terminals and external launchers. The base wheel does not require Nim; native Nim behavior and performance remain platform-dependent and require a local build. TUI screenshots are representative only: renderer/font limitations do not support a pixel-perfect claim.

See [docs/SECURITY.md](docs/SECURITY.md) for our security policy and responsible disclosure.

---

## Documentation

See [docs/README.md](docs/README.md) for the full index:

| | |
|--|--|
| [Quick Start](docs/user-guides/quick-start.md) | [Configuration](docs/user-guides/configuration.md) |
| [Tools Reference](docs/reference/tools.md) | [Architecture](docs/architecture/system-architecture.md) |
| [Developer Guide](docs/developer-guides/developer-guide.md) | [API Reference](docs/reference/api.md) |

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Run tests and lint (`pytest tests/ && ruff check aura_cli tests scripts`)
4. Commit and open a Pull Request

See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for full guidelines.

---

## License

BSD-3-Clause — see [LICENSE](LICENSE)

Copyright (c) 2025–2026 Aura Core Team. All rights reserved.

---

## Acknowledgments

- **AuraPaint** — native AuraCli ANSI art editor; inspired by and retaining MIT attribution from [Textual Paint](https://github.com/1j01/textual-paint) by Isaiah Odhner
- [Textual](https://github.com/Textualize/textual) — TUI framework
- [Rich](https://github.com/Textualize/rich) — Terminal rendering
- [LiteLLM](https://github.com/BerriAI/litellm) — Unified LLM API
