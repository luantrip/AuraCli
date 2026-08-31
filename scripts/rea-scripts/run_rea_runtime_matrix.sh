#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCENARIO_DIR="${SCENARIO_DIR:-${PROJECT_ROOT}/docs/rea-study/scenarios}"
OUTPUT_DIR="${OUTPUT_DIR:-${PROJECT_ROOT}/.aura/rea-study/rea-captures}"
LOCAL_REA_RUNTIME="${PROJECT_ROOT}/.local/runtimes/rea-agents"
REA_RUNTIME="${REA_RUNTIME:-${LOCAL_REA_RUNTIME}}"

if [[ ! -d "${REA_RUNTIME}/dist" ]]; then
  SOURCE_REA_RUNTIME="${PROJECT_ROOT}/../Dev/REA/REA"
  if [[ -d "${SOURCE_REA_RUNTIME}/dist" ]]; then
    REA_RUNTIME="${SOURCE_REA_RUNTIME}"
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
  fi
fi

if [[ ! -d "${REA_RUNTIME}/dist" ]]; then
  printf 'REA runtime unavailable; no capture was started: %s\n' "${REA_RUNTIME}" >&2
  exit 3
fi

mkdir -p "${OUTPUT_DIR}"
for scenario in "$@"; do
  scenario_path="${SCENARIO_DIR}/${scenario}.json"
  output_path="${OUTPUT_DIR}/${scenario}.capture.json"
  if [[ ! -f "${scenario_path}" ]]; then
    printf 'Scenario not found: %s\n' "${scenario_path}" >&2
    exit 2
  fi
  "${PROJECT_ROOT}/scripts/rea-scripts/run_rea_aura_capture.sh" \
    "${scenario_path}" \
    "${output_path}"
done
