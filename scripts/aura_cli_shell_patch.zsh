# Aura CLI — PATH do venv, alias e defaults dos agentes (AGI/Ops/ADK).
# Fonte única: também referenciado por scripts/install_aura_cli.sh

: "${AURA_CLI_ROOT:=$HOME/aura-cli}"

# Agentes: bridge ADK ligado por padrão (Aura AGI / Aura Ops)
export AURA_USE_ADK_BRIDGE="${AURA_USE_ADK_BRIDGE:-true}"

if typeset -f path_prepend >/dev/null 2>&1; then
  path_prepend "${AURA_CLI_ROOT}/.venv/bin"
else
  case ":$PATH:" in
    *":${AURA_CLI_ROOT}/.venv/bin:"*) ;;
    *)
      [[ -d "${AURA_CLI_ROOT}/.venv/bin" ]] && export PATH="${AURA_CLI_ROOT}/.venv/bin:$PATH"
      ;;
  esac
fi

if command -v aura >/dev/null 2>&1; then
  alias Aura=aura
fi

function aura_ci_gate() {
  "${AURA_CLI_ROOT}/.venv/bin/python" \
    "${AURA_CLI_ROOT}/scripts/operational_release_gate.py" --json "$@"
}
