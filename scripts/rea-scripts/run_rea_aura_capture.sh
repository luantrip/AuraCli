#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REA_ROOT="${REA_ROOT:-/Users/macbookpro/Desktop/Projetos/Dev/REA/REA}"
LOCAL_REA_RUNTIME="${PROJECT_ROOT}/.local/runtimes/rea-agents"
REA_RUNTIME="${REA_RUNTIME:-${LOCAL_REA_RUNTIME}}"
SCENARIO="${1:-${PROJECT_ROOT}/docs/rea-study/scenarios/aura-help.json}"
OUTPUT="${2:-${PROJECT_ROOT}/docs/rea-study/evidence/aura-help.capture.json}"

if [[ ! -d "${REA_RUNTIME}/dist" ]]; then
  if [[ -d "${REA_ROOT}/dist" ]]; then
    REA_RUNTIME="${REA_ROOT}"
    printf 'Using source REA runtime: %s\n' "${REA_RUNTIME}" >&2
  fi
fi

if [[ ! -d "${REA_RUNTIME}/dist" ]]; then
  CACHED_REA_RUNTIME="${REA_NPX_RUNTIME:-}"
  if [[ -z "${CACHED_REA_RUNTIME}" && -d "${HOME:-}/.npm/_npx" ]]; then
    CACHED_REA_RUNTIME="$(find "${HOME}/.npm/_npx" \
      -path '*/node_modules/rea-agents/dist/cli-runtime/cli.js' \
      -print -quit 2>/dev/null | sed 's#/dist/cli-runtime/cli.js$##')"
  fi
  if [[ -n "${CACHED_REA_RUNTIME}" && -d "${CACHED_REA_RUNTIME}/dist" ]]; then
    REA_RUNTIME="${CACHED_REA_RUNTIME}"
    printf 'Using fallback REA runtime: %s\n' "${REA_RUNTIME}" >&2
  fi
fi

if [[ ! -f "${SCENARIO}" ]]; then
  printf 'Scenario not found: %s\n' "${SCENARIO}" >&2
  exit 2
fi

if [[ ! -f "${REA_ROOT}/scripts/rea.mjs" ]]; then
  printf 'REA source not found: %s\n' "${REA_ROOT}" >&2
  exit 2
fi

if [[ ! -d "${REA_RUNTIME}/dist" ]]; then
  printf 'REA runtime is not built. Set REA_RUNTIME to a compiled REA package or run npm ci && npm run build:cached in %s\n' "${REA_ROOT}" >&2
  exit 3
fi

mkdir -p "$(dirname "${OUTPUT}")"
node "${REA_RUNTIME}/scripts/rea.mjs" capture-process "${SCENARIO}" --json > "${OUTPUT}"
printf 'Capture written to %s\n' "${OUTPUT}"
