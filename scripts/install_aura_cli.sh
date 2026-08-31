#!/usr/bin/env bash
# Instala Aura CLI no venv do projeto e aplica o patch no ~/.zshrc
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AURA_CLI_ROOT="$ROOT"
ZSHRC="${ZSHRC:-$HOME/.zshrc}"
MARK_BEGIN="# >>> aura-cli installer >>>"
MARK_END="# <<< aura-cli installer <<<"

PATCH_BLOCK=$(cat <<EOF
${MARK_BEGIN}
export AURA_CLI_ROOT="${AURA_CLI_ROOT}"
[[ -f "\${AURA_CLI_ROOT}/scripts/aura_cli_shell_patch.zsh" ]] && source "\${AURA_CLI_ROOT}/scripts/aura_cli_shell_patch.zsh"
${MARK_END}
EOF
)

echo "==> Aura CLI root: ${AURA_CLI_ROOT}"

if [[ ! -d "${AURA_CLI_ROOT}/aura_cli" ]]; then
  echo "Erro: diretório aura_cli não encontrado em ${AURA_CLI_ROOT}" >&2
  exit 1
fi

echo "==> Criando/atualizando venv..."
python3 -m venv "${AURA_CLI_ROOT}/.venv"
"${AURA_CLI_ROOT}/.venv/bin/python" -m pip install -U pip wheel
"${AURA_CLI_ROOT}/.venv/bin/pip" install -e "${AURA_CLI_ROOT}[dev]"
"${AURA_CLI_ROOT}/.venv/bin/pip" install --no-build-isolation -e "${AURA_CLI_ROOT}/packages/aura-cli-nim"

echo "==> Versão instalada:"
"${AURA_CLI_ROOT}/.venv/bin/aura" --version

if [[ ! -f "${ZSHRC}" ]]; then
  touch "${ZSHRC}"
fi

backup="${ZSHRC}.aura-cli.bak"
cp "${ZSHRC}" "${backup}"

"${AURA_CLI_ROOT}/.venv/bin/python" - \
  "${ZSHRC}" "${PATCH_BLOCK}" "${MARK_BEGIN}" "${MARK_END}" <<'PY'
from pathlib import Path
import re
import sys

zshrc = Path(sys.argv[1])
text = zshrc.read_text(encoding="utf-8", errors="replace")
block = sys.argv[2]

begin = sys.argv[3]
end = sys.argv[4]
pattern = re.compile(
    re.escape(begin) + r".*?" + re.escape(end) + r"\n?",
    re.DOTALL,
)
if pattern.search(text):
    text = pattern.sub(block + "\n", text)
else:
    if not text.endswith("\n"):
        text += "\n"
    text += "\n" + block + "\n"

# Remove bloco legado comentado (PATH manual antigo)
legacy = re.compile(
    r"# Aura CLI venv \(COMENTADO.*?\n(?:#.*\n)*",
    re.MULTILINE,
)
text = legacy.sub("", text)

zshrc.write_text(text, encoding="utf-8")
print(f"==> Patch aplicado em {zshrc}")
PY

echo ""
echo "Backup anterior: ${backup}"
echo "Pronto. Execute: source ~/.zshrc   (ou abra um novo terminal)"
echo "Comandos: aura   ou   Aura"
