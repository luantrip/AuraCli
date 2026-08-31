#!/usr/bin/env bash
# Aura CLI — Full Build Pipeline (Python + optional Nim)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_PYTHON="$PROJECT_ROOT/.venv/bin/python"

if [[ ! -x "$VENV_PYTHON" ]]; then
    echo "Creating project virtual environment..."
    python3 -m venv "$PROJECT_ROOT/.venv"
fi

echo "═══════════════════════════════════════════"
echo "  Aura CLI Build Pipeline"
echo "═══════════════════════════════════════════"

# 1. Python package
echo ""
echo "▸ Installing Python package..."
"$VENV_PYTHON" -m pip install -e "$PROJECT_ROOT[dev]" -q
echo "  ✓ Python package installed"

# 2. Nim binaries (optional)
echo ""
if "$SCRIPT_DIR/build_nim.sh" --check >/dev/null 2>&1; then
    echo "▸ Building Nim binaries..."
    "$SCRIPT_DIR/build_nim.sh"
else
    echo "▸ Nim compiler not found — skipping binary build"
    echo "  ℹ Install Nim: https://nim-lang.org/install.html"
    echo "  ℹ Python fallbacks will be used for forge analysis"
fi

# 3. Verify
echo ""
echo "▸ Running tests..."
"$VENV_PYTHON" -m pytest "$PROJECT_ROOT/tests" -q --tb=short

echo ""
echo "═══════════════════════════════════════════"
echo "  ✓ Build complete"
echo "═══════════════════════════════════════════"
