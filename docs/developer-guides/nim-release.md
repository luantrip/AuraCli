# Nim Release Guide — Aura CLI

---

## Layout

`modules_nim/` contains the Nim source code. `bin/` is the canonical location
for compiled binaries included in the repository. `scripts/build_nim.sh`
produces and stages artefacts into `bin/`.

The runtime resolves binaries from the installed `aura_cli_nim` package first,
then falls back to the repository's `bin/` directory during development.
Files in `build/`, `dist/`, `.mypy_cache/`, `*.egg-info/`, and `__pycache__/`
are generated outputs, not sources.

---

## Platform Matrix

| Platform | Status |
|----------|--------|
| `macos-x86_64` | Complete — pre-built binaries included in `bin/` |
| `macos-aarch64` | Build locally with `./scripts/build_nim.sh` |
| `linux-x86_64` | **Incomplete** — `notebook.so` is absent; build locally |
| `windows-x86_64` | Not currently supported |

> **Linux note:** The `linux-x86_64` executables have the correct format and
> permissions but the set is deliberately considered incomplete and
> unpublishable while `notebook.so` is absent. Do not reuse a binary from
> another architecture.

---

## Building from Source

Requires Nim >= 1.6.0.

```bash
./scripts/build_nim.sh --release
```

The build script:
1. Compiles all modules in `modules_nim/`
2. Copies artefacts to `bin/`
3. Normalises permissions
4. Writes `SHA256SUMS` for both source and staging areas

---

## Verification

```bash
python scripts/verify_nim_release.py <platform-tag>
```

Validation requires:
- Six executables present
- `notebook` shared library present
- Correct native binary format
- Matching SHA256 hashes
- Safe permissions

The `--smoke` flag runs entry points and loads the library — only when the
target matches the current host. In a cross-target audit, format, hash, and
permission checks still run; a warning is emitted that the smoke test was
skipped.

---

## Release Checklist

1. Update sources in `modules_nim/` and run `./scripts/build_nim.sh --release`
   on the supported target.
2. Run `python scripts/verify_nim_release.py <tag>`. Fix any failures before
   proceeding.
3. Build the wheel in a clean tree. The official workflow installs into a new
   virtual environment and confirms that all seven artefacts are resolved.
4. Publish only wheels and release files produced by jobs that passed
   completely. Never manually copy an artefact between platform tags.

---

## Binary Behaviour Notes

- `sentinel` is validated by format and permissions only during cross-target
  audits, because older builds interpret the first argument as a project root.
  Use the current build for any `--version` or smoke invocation.
- `notebook` is a shared library; load it with `ctypes.CDLL` to verify
  (the smoke test does this automatically).
- A missing or failing binary causes the system to use the Python fallback
  where that path is implemented, or to skip the feature gracefully.

---

*Aura CLI — Nim Release Guide*
