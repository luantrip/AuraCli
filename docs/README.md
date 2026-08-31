# Aura CLI — Documentation

This is the canonical documentation index. User guides, developer guides,
architecture docs, and reference material describe the current product.

## Start here

- Usage: [Quick Start](./user-guides/quick-start.md)
- Development: [Developer Guide](./developer-guides/developer-guide.md)
- Architecture: [System Architecture](./architecture/system-architecture.md)
- Diagnostics: [Troubleshooting](./user-guides/troubleshooting.md)
- Evaluation and reliability: [Evaluation and Reliability](./reference/evaluation-and-reliability.md)
- Founder business skills: [Founder Business Skills](./reference/founder-business-skills.md)
- Contributing: [CONTRIBUTING](./CONTRIBUTING.md)

Local links in this index and other documents are validated by
`python scripts/check_docs.py` in CI.

## Structure

```
docs/
├── architecture/       Design and technical decisions
├── developer-guides/   For contributors and integrators
├── user-guides/        For end users
├── reference/          Specifications and quick lookup
├── CHANGELOG.md        Version history
├── CONTRIBUTING.md     Contribution guide
└── SECURITY.md         Security policy and disclosure
```

---

## For Users

| Document | Content |
|----------|---------|
| [quick-start](./user-guides/quick-start.md) | Installation and first steps |
| [configuration](./user-guides/configuration.md) | API keys, models, themes |
| [tools](./user-guides/tools.md) | Integrated tools catalogue |
| [evaluation-and-reliability](./reference/evaluation-and-reliability.md) | Arena, MCP, skills, resilience, and reports |
| [workers](./user-guides/workers.md) | AGI and Ops workers |
| [tui-tools](./user-guides/tui-tools.md) | TUI tools (AuraPaint, File Manager, Monitor) |
| [sessions](./user-guides/sessions.md) | Sessions, checkpoints, tangent |
| [approvals](./user-guides/approvals.md) | Auto-run and confirmations |
| [agent-editing](./user-guides/agent-editing.md) | How agents edit code |
| [refactoring](./user-guides/refactoring.md) | Automated refactoring |
| [troubleshooting](./user-guides/troubleshooting.md) | Problem resolution |

---

## For Developers

| Document | Content |
|----------|---------|
| [developer-guide](./developer-guides/developer-guide.md) | Development overview |
| [testing](./developer-guides/testing.md) | How to test |
| [release-gate](./developer-guides/release-gate.md) | Operational release checklist |
| [plugins](./developer-guides/plugins.md) | Creating plugins and extensions |
| [adk-guide](./developer-guides/adk-guide.md) | Agent Development Kit |
| [tui-components](./developer-guides/tui-components.md) | Textual widgets |
| [workflows](./developer-guides/workflows.md) | YAML workflow system |
| [nim-release](./developer-guides/nim-release.md) | Nim binary release and verification |
| [CONTRIBUTING](./CONTRIBUTING.md) | Contribution guide |
| [scripts](../scripts/README.md) | Build, install, and operational scripts |

---

## Architecture

| Document | Content |
|----------|---------|
| [system-architecture](./architecture/system-architecture.md) | Overall system design |
| [application-layer](./architecture/application-layer.md) | Use cases, contracts, and Application layer rules |
| [nim-modules](./architecture/nim-modules.md) | Nim Powerpack — native binaries |
| [memory-system](./architecture/memory-system.md) | Memory, vectors, embeddings |
| [cache-system](./architecture/cache-system.md) | Cache strategies |
| [consciousness](./architecture/consciousness.md) | Skills and cognitive model (personas) |
| [tui-windows](./architecture/tui-windows.md) | TUI window and screen model |
| [cli-ui-composition](./architecture/cli-ui-composition.md) | CLI UI composition |

---

## Reference

| Document | Content |
|----------|---------|
| [api](./reference/api.md) | Python API reference |
| [tools](./reference/tools.md) | Tool specifications |
| [project-structure](./reference/project-structure.md) | Project structure |
| [codebase-map](./reference/codebase-map.md) | Cross-cutting responsibility map |
| [generated-artifacts](./reference/generated-artifacts.md) | Runtime and test-generated directories and files |
| [migration-surfaces](./reference/migration-surfaces.md) | Removed facades, public re-exports, and pending migrations |
| [documentation-status](./reference/documentation-status.md) | Documentation conventions and native product identity |
| [optional-deps](./reference/optional-deps.md) | Optional dependencies |
| [environment-variables](./reference/environment-variables.md) | Environment variables |
| [founder-business-skills](./reference/founder-business-skills.md) | Native business validation workflow |

---

## Security and History

| Document | Content |
|----------|---------|
| [SECURITY](./SECURITY.md) | Security policy and responsible disclosure |
| [CHANGELOG](./CHANGELOG.md) | Version history |
