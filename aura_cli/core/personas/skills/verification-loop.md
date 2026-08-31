---
name: verification-loop
description: Use this skill after completing a feature, before creating a PR, or when you want to ensure quality gates pass. Runs build, type checks, lint, tests with coverage, security scan, and diff review, then produces a structured PASS/FAIL report.
version: 1.0.0
author: Aura Core Team
---

# Verification Loop Skill

A comprehensive quality verification system to run before creating PRs or after significant changes.

## When to Use

- After completing a feature or significant code change
- Before creating a PR
- After refactoring
- When you want a full quality status

## Verification Phases

Run all phases in order. **Stop at first FAIL and fix before continuing.**

### Phase 1: Build Verification
```bash
# Verify the package imports without errors
python -c "import aura_cli" && echo "✅ Build OK"
# OR verify entry point
python -m aura_cli --version 2>&1 | head -3
```

If build fails → STOP, fix the import error, then continue.

### Phase 2: Type Check
```bash
mypy aura_cli/ --ignore-missing-imports 2>&1 | tail -10
```

Report all type errors. Fix CRITICAL ones (those blocking runtime) before continuing.

### Phase 3: Lint Check
```bash
ruff check aura_cli/ tests/ 2>&1 | tail -15
```

Fix all errors. Warnings are acceptable but should be noted.

### Phase 4: Test Suite with Coverage
```bash
pytest --cov=aura_cli --cov-report=term-missing -q 2>&1 | tail -25
```

Report:
- Total tests: X
- Passed: X
- Failed: X
- Coverage: X% (target: ≥80%)

If coverage < 80% → identify uncovered critical paths and add tests.

### Phase 5: Security Scan
```bash
# Check for accidental secrets
grep -rn "sk-\|api_key\s*=\s*['\"]" --include="*.py" aura_cli/ 2>/dev/null | head -5

# Check for debug/print statements left in
grep -rn "^print\b\|pdb\.set_trace\|breakpoint()" --include="*.py" aura_cli/ 2>/dev/null | head -5
```

### Phase 6: Diff Review
```bash
git diff --stat
git diff --name-only HEAD~1 2>/dev/null || git status --short
```

Review each changed file for:
- Unintended changes
- Missing error handling
- Edge cases not covered

## Output Format

After all phases, produce this report:

```
VERIFICATION REPORT
===================

Build:     ✅ PASS
Types:     ✅ PASS (0 errors)
Lint:      ✅ PASS (0 warnings)
Tests:     ✅ PASS (142/142 passed, 84% coverage)
Security:  ✅ PASS (no issues found)
Diff:      3 files changed, 47 insertions(+), 12 deletions(-)

Overall: ✅ READY for PR

Issues to Fix:
(none)
```

Or if there are failures:

```
VERIFICATION REPORT
===================

Build:     ✅ PASS
Types:     ❌ FAIL (3 errors)
Lint:      ⚠️  WARN (2 warnings)
Tests:     ❌ FAIL (138/142, 71% coverage)
Security:  ✅ PASS
Diff:      5 files changed

Overall: ❌ NOT READY — fix before PR

Issues to Fix:
1. [TYPES] aura_cli/core/engine.py:45 — Parameter 'data' implicitly has Any type
2. [TYPES] aura_cli/core/utils.py:12 — Return type missing annotation
3. [TYPES] aura_cli/cli/main.py:78 — Incompatible return type
4. [TESTS] Coverage 71% < 80% threshold — add tests for error paths in core/engine.py
```

## Continuous Mode

For long development sessions, run verification every:
- After completing each function or method
- After finishing a component or module
- Before switching to a different part of the codebase

Mental checkpoint: "Would I be comfortable creating a PR right now?"

## PR Readiness Criteria

All must be ✅ before creating a PR:

- [ ] `python -c "import aura_cli"` exits without error
- [ ] `mypy aura_cli/` — no critical errors
- [ ] `ruff check aura_cli/ tests/` — clean
- [ ] `pytest --cov=aura_cli` — ≥80% coverage, all tests pass
- [ ] No hardcoded secrets or debug statements in diff
- [ ] Diff reviewed — no unintended changes
