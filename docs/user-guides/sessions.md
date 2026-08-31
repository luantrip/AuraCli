# Session Management

Aura CLI provides session management to save and restore conversation state.

The session commands are available in the interactive CLI. The same persistence
use case is used by `/session load` and the shorter `/resume` command.

---

## Overview

Sessions allow you to:
- Save your current work state
- Resume work in a later run
- Track conversation and project history

---

## Creating Sessions

### Save Current Session

```
› /session save my-project
```

This saves:
- Conversation history
- Current context
- Project state
- Tool usage history
- Configuration

### Session Location

Sessions are stored in:
- `~/.aura/sessions/` — user sessions
- `.aura/sessions/` — project-scoped sessions

---

## Loading Sessions

### Load Session

```
› /session load my-project
```

Restores:
- Conversation history
- Context
- Project state
- Configuration

### Resume From the Command Line

Start Aura and restore a saved session before opening the prompt:

```bash
aura --resume <id-or-prefix>
```

The reference can be a complete ID, a unique ID prefix, or an exact session
name. Inside an active session, the equivalent short command is:

```text
/resume <id-or-prefix-or-name>
```

An ambiguous or missing reference stops with an explicit message and does not
replace the current conversation.

External sessions can be imported as historical context using a direct JSON,
JSONL, or documented session directory path. Namespaces make the origin clear:

```bash
aura --resume file:/path/to/session.jsonl
aura --resume grok:/path/to/grok/session-directory
aura --resume codex:/path/to/rollout.jsonl
```

The interactive equivalent is `/resume file:/path/to/session.jsonl`. Imported
tool calls, shell commands, and approvals are never executed; they are omitted
and reported in the imported session metadata. Provider discovery by bare
external ID is supported for Grok and Codex when their standard session homes
are available. Ambiguous prefixes are rejected with the matching artifacts;
Claude and OpenCode currently require a direct path.

When the imported session records a different workspace or model, startup shows
a confirmation with the detected divergence. Cancelling leaves the current
workspace untouched. The interactive `/resume` path blocks divergent imports
and directs the user to the startup command, where confirmation is explicit.
External sandbox, approval, and permission metadata is displayed as unverified;
it never changes Aura's active policy automatically.

### List Sessions

```
› /session list
```

Shows all available sessions.

---

## Session Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/session save <name>` | Save current session | `/session save api-project` |
| `/session load <name>` | Load session | `/session load api-project` |
| `/session list` | List all sessions | `/session list` |
| `/session delete <name>` | Delete session | `/session delete old-project` |
| `/session info <name>` | Show session info | `/session info api-project` |
| `/resume <id|prefix|name>` | Resume a saved session | `/resume 01a1633f` |

---

## Session Contents

### What Is Saved

```json
{
    "name": "my-project",
    "created_at": "2026-01-15T10:00:00",
    "updated_at": "2026-01-15T15:30:00",
    "conversation_history": [],
    "context": {
        "project_path": "/path/to/project",
        "files_analyzed": [],
        "tools_used": []
    },
    "state": {
        "current_model": "gemini/gemini-2.5-flash",
        "theme": "nebula-dark",
        "settings": {}
    }
}
```

---

## Related Documentation

- [Quick Start](./quick-start.md) — Getting started
- [Configuration](./configuration.md) — Configuration guide

---

**Version**: 0.1.0
**Last Updated**: 2026
