# Approvals, Auto-Run, and Confirmations

Aura CLI protects sensitive operations (file editing, Git, Docker, shell) using:

- **Diff approval windows** (`[A]ccept / [R]eject / Accept [A]ll?`) for file changes.
- **Standard confirmation prompts** for risky operations (backup/restore, commit, Docker, shell).
- **Confirmation-free execution mode** for advanced users.

---

## Diff Approval Windows (A/R/A)

For write tools (`write_file`, `edit_file`, `replace_in_file` via AGI):

- Aura shows a **compact diff** with:
  - Target file.
  - Added/removed lines.
  - Addition/removal counter.
- Then displays the prompt:

```
[A]ccept / [R]eject / Accept [A]ll?
```

**Shortcuts:**
- `A` or Enter: accept the current change.
- `R`: reject the change.
- `T` (Accept All): accept this and **all future** changes (activates `skip_confirmations`).

When `T` is used, **confirmation-free mode** stays active until manually disabled.

---

## Confirmation-Free Mode (Skip Confirmations)

Use this mode when you want Aura to automatically apply operations that the
current flow has already validated (edits, commits, Docker, filtered shell).

### How to toggle

- **Keyboard shortcut:** `Shift+Tab`
- **Direct command:** `/auto-run`

On toggle, Aura displays:

```
ℹ Confirmation-free execution enabled
```
or
```
ℹ Confirmation-free execution disabled
```

### Where the mode appears in the UI

- **In the prompt:** `(skip)` indicator next to the cursor.
- **In the bottom toolbar:** **⚡ Auto-run** text when the mode is active.
- **In the status bar** (when visible): aligned to the same state.

### Practical Effect

With `skip_confirmations` **enabled**:

- `run_shell_command`: executes directly, still respecting security filters.
- `write_file` / `edit_file` / `restore_backup`: execute without an additional prompt.
- `git_commit` / `git_commit_smart`: create commits immediately.
- `docker_exec`, `docker_build`, `docker_compose`: execute after the context banner.

With `skip_confirmations` **disabled**:

- All of the above operations request explicit confirmation before proceeding.

---

## Unified Confirmation Prompts

Internally, Aura uses a central confirmation utility with the following behaviour:

- Reads from stdin robustly (no conflicts with async loops).
- Accepts `y/yes`, `n/no`, or Enter (uses the default value).
- On `Ctrl+C`, `ESC`, or EOF: the operation is cancelled with a clear message.

This applies to:

- Backup restorations.
- Git commits and smart commits.
- Docker container command execution.
- Docker builds and critical `docker-compose` operations.

---

## Usage Recommendations

**Standard mode (recommended):**
- Keep confirmation prompts enabled.
- Use the A/R/T windows to review diffs before accepting.

**Advanced mode (power user):**
- Enable `skip_confirmations` only when:
  - In a controlled environment (e.g. local dev).
  - You have reviewed the plan the AGI/Ops is about to execute.

**When in doubt:**
- Disable confirmation-free mode (`Shift+Tab`).
- Let Aura ask before each sensitive operation.

---

## File Operation Summary

After each model response, if files were read/created/edited, Aura displays a
**file operation summary after** the response (not before), to preserve reading
flow. When there are many operations (e.g. more than 12 files), the summary is
shown in compact (single-line) format.

---

**Version**: 0.1.0
**Last Updated**: 2026
