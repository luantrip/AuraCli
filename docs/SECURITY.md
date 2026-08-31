# Security Policy

## How API Keys Are Stored

API keys use the OS keyring (macOS Keychain, GNOME Keyring/Secret Service, or
Windows Credential Manager) by default. The configuration file represents the
shape of the configuration but should not receive live secrets as a normal
workflow.

If the secure backend is unavailable, Aura fails **fail-closed** and does not
silently downgrade to plaintext. An insecure backend requires an explicit opt-in
for controlled local scenarios.

**Recommendations:**
- Set restrictive permissions on local files: `chmod 600 ~/.aura/config.json`
- Do not include `~/.aura/` or `.aura/` in version control
- Use `/settings` or environment variables (e.g. `AURA__API_KEYS__GOOGLE`)
  without logging the values

## Data That Stays Local

Aura CLI is designed to keep your code local:

- Source code stays local by default, but file excerpts, tool results, and
  context may be sent when included in a prompt to the configured provider.
- Prompts and conversation context are sent only to the LLM provider chosen in
  your configuration, and only when a real provider operation is initiated.
- **Memory and session data** are stored locally in `~/.aura/` and the
  project's `.aura/` directory.
- **Nim Powerpack binaries** run entirely offline with no network calls.
- **Vector embeddings** (when enabled) are computed locally via **fastembed**
  (ONNX Runtime) when the environment supports `onnxruntime>=1.17`. On
  macOS 10.15, the package is not installed by default and Chroma uses its
  default embeddings.

### What Is Sent to LLM Providers

- Your natural-language prompts
- System context summaries (project structure, file names — not full file
  content unless you explicitly request it)
- Tool call results needed for LLM reasoning

## Tool Confirmation System

Confirmation is contextual and depends on the active policy. Normal mode
requests approval for risky operations including writes, shell, mutating Git,
Docker, and infrastructure. Auto-run mode may skip the prompt only when the
policy classifies the operation as permitted; unavailable policy, failed
confirmation, or an unclassified risky operation blocks execution.

Read-only operations may run without a prompt when the boundary and policy
allow it. Shell execution runs without `shell=True`, with a timeout, output
limit, isolated process group, and background supervisor with PID/status/cancel.

AGI mode (`/agi`) does not guarantee complete rollback. Delegated operations
maintain snapshots/outcomes, and workflows with possible side effects require
reconciliation rather than silent fallback to chat. Use `/checkpoint` when the
flow supports it and review artifacts before accepting a change.

## Nim Powerpack Integrity

The Nim Powerpack is optional and is not required by the base Python wheel.
This checkout ships compiled macOS (`macos-x86_64`) binaries in `bin/`.
Binaries for other platforms must be built locally:

```bash
./scripts/build_nim.sh
```

Source code is available in `modules_nim/`. To verify or rebuild any binary,
use the build script above. If a binary is unavailable or fails, the system
falls back to Python where that path is implemented.

## Workspace Limits and Tests

Relative paths, external absolute paths, and symlinks that resolve outside the
canonical workspace are rejected by workspace-scoped services. The offline
validation pass (macOS, `tests/unit` and `tests/e2e`) passes 4,656 tests
without real providers, network, Docker, remote Git, or `tests/integration`;
remaining failures are platform-specific (native Nim, `aura_cli_nim`, and the
`fastembed` extra). This scope does not prove physical-terminal compatibility
or cross-platform Nim performance.

## Third-Party Dependencies

- **ChromaDB (embedded-only):** Aura uses ChromaDB strictly in embedded local
  mode (`PersistentClient`/`Client`), never as a network server (`HttpClient`).
  Known ChromaDB advisories (PYSEC-2026-311, CVE-2026-45830/45831/45833) affect
  only the Python server (authorization bypass between tenants and code injection
  in server endpoints) and are not reachable in the embedded, single-process,
  unauthenticated usage adopted here. Do not introduce `chromadb.HttpClient` or
  run a ChromaDB server without a dedicated security review.
- The dependency surface is monitored with `pip-audit`; re-run after dependency
  updates.

## Reporting Security Vulnerabilities

If you discover a security vulnerability, please report it responsibly:

1. **Do NOT open a public GitHub issue** for security vulnerabilities.

2. **Preferred:** Use
   [GitHub Security Advisories](https://github.com/luantrip/AuraCli/security/advisories/new)
   to report privately.

3. **Alternative:** Contact the maintainer directly (see the repository owner's
   profile for contact information).

Include in your report:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

The goal is to acknowledge reports within 48 hours and provide a fix or
mitigation plan within 7 days for critical issues.

## Supported Versions

| Version | Security Updates |
|---------|-----------------|
| 0.1.x   | Active          |

## Security Best Practices for Users

- Keep your Aura CLI installation up to date
- Review tool confirmations carefully before approving write operations
- Use `/checkpoint` before significant autonomous operations
- Restrict permissions on `~/.aura/config.json` to your user only
- Rotate your API keys periodically
