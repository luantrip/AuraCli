# Evaluation and Reliability

AuraCli keeps evaluation and resilience native to the Python core. The layer
does not require a specific model provider.

## Capabilities

- **Scheduler:** persist runs, claim work, retry failures, cancel, and resume
  interrupted executions with `RunScheduler`.
- **Evaluation:** compare candidates blindly with weighted criteria, calculate
  quality/diversity metrics, and save JSON/Markdown reports.
- **Profiles:** isolate credentials and run metadata by profile with atomic
  writes and restricted file permissions. Set `AURA_PROFILE` to select a named
  profile; named profiles use `AURA_HOME/profiles/<profile>/config.json` and
  an isolated keyring namespace, while the default profile remains compatible.
- **Resilience:** use bounded exponential backoff, idempotency keys, and a
  composable request middleware chain.
- **Fault testing:** inject named deterministic failures in tests without
  changing production call sites.
- **Arena:** persist a bracket and write an evaluation report under its artifact
  directory.

## CLI

```text
/arena [--quick] [--agents N] [--seed N] <task>
/skill list|install|remove|status|pack|search ...
/mcp status|manifest|start ...
```

MCP is read-only by default. Writes require `--allow-writes` and continue to
use AuraCli's tool policy checks.

## Python contracts

```python
from aura_cli.core.evaluation import RunScheduler, select_best
from aura_cli.core.reliability import ProfileStore, RetryPolicy, retry_call
```

The scheduler and stores use atomic JSON persistence. Reports are written with
`save_report(report, path)`; Arena creates `evaluation.json` and its matching
Markdown file automatically.

## Validation

The current full suite covers the native layer and reports `4911 passed` with
no skipped tests or warnings on the maintained macOS environment. Provider-
specific authentication protocols and NotebookLM-only APIs are intentionally
not part of AuraCli.
